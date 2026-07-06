import asyncio
from .request import Request, RequestState
from dataclasses import dataclass
from torch import Tensor
import torch


@dataclass
class ScheduleReqs:
    requests: list[Request]
    is_prefill: bool


@dataclass
class ModelInput:
    req_ids: list[str]
    flat_input_ids: Tensor
    req_indptr_cpu: Tensor
    position_index: Tensor


class Scheduler:
    def __init__(self, queue: asyncio.Queue[Request], max_prefill_reqs: int = 64):
        self.waiting = list()
        self.running = list()
        self.finished = list()
        self.queue = queue
        self.max_prefill_reqs = max_prefill_reqs

    async def add_requests(self, requests: list[Request]):
        for req in requests:
            await self.queue.put(req)

    async def schedule(self) -> tuple[ScheduleReqs | None, ScheduleReqs | None]:
        decode_reqs = None
        if self.running:
            decode_reqs = ScheduleReqs(requests=list(self.running), is_prefill=False)

        prefill_reqs = None
        waiting_reqs = []
        if decode_reqs is None:
            waiting_reqs.append(await self.queue.get())

        while len(waiting_reqs) < self.max_prefill_reqs:
            try:
                waiting_reqs.append(self.queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        self.waiting = waiting_reqs
        if self.waiting:
            for req in self.waiting:
                req.state = RequestState.RUNNING
            prefill_reqs = ScheduleReqs(requests=self.waiting, is_prefill=True)
            self.running.extend(self.waiting)
            self.waiting = []

        return prefill_reqs, decode_reqs

    def build_model_input(self, schedule_reqs: ScheduleReqs, device) -> ModelInput:
        flat_tokens = [
            tok for req in schedule_reqs.requests for tok in req.input_tokens
        ]
        flat_input = torch.tensor(flat_tokens, dtype=torch.long, device=device)

        input_lens = torch.tensor(
            [len(req.input_tokens) for req in schedule_reqs.requests],
            dtype=torch.long,
        )
        req_indptr_cpu = torch.cat(
            [torch.tensor([0], dtype=torch.long), torch.cumsum(input_lens, 0)]
        )

        req_ids = [req.req_id for req in schedule_reqs.requests]

        if schedule_reqs.is_prefill:
            total_tokens_num = req_indptr_cpu[-1]
            req_len_cpu = req_indptr_cpu[1:] - req_indptr_cpu[:-1]
            # position_index shape: (total_tokens_num,)
            position_index = torch.arange(total_tokens_num) - torch.repeat_interleave(
                req_indptr_cpu[:-1],
                req_len_cpu,
            )
            position_index = position_index.to(device)
        else:
            # (req_num,)
            position_index = torch.tensor(
                [req.computed_tokens for req in schedule_reqs.requests], device=device
            )
        return ModelInput(req_ids, flat_input, req_indptr_cpu, position_index)

    def process_output(self, schedule_reqs, gen_tokens: Tensor, stop_ids):
        gen_tokens_list = gen_tokens.detach().cpu().view(-1).tolist()
        for req, tok in zip(schedule_reqs.requests, gen_tokens_list):
            req.computed_tokens += len(req.input_tokens)
            if tok in stop_ids:
                req.state = RequestState.FINISHED
                self.finished.append(req)
                continue

            req.input_tokens = [tok]
            req.output_tokens.append(tok)
            if len(req.output_tokens) >= req.max_new_tokens:
                req.state = RequestState.FINISHED
                self.finished.append(req)
        self.running = [
            req for req in self.running if req.state != RequestState.FINISHED
        ]

    def drain_finished_reqs(self):
        finished = self.finished
        self.finished = []
        return finished

    def fail_all(self, error: Exception) -> list[Request]:
        done_reqs = []
        seen_req_ids = set()

        def add_finished(req: Request):
            if req.req_id in seen_req_ids:
                return
            seen_req_ids.add(req.req_id)
            done_reqs.append(req)

        def add_failed(req: Request):
            if req.req_id in seen_req_ids:
                return
            seen_req_ids.add(req.req_id)
            req.error = error
            req.state = RequestState.FINISHED
            done_reqs.append(req)

        for req in self.finished:
            add_finished(req)
        for req in self.running:
            add_failed(req)
        for req in self.waiting:
            add_failed(req)

        while True:
            try:
                add_failed(self.queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        self.waiting = []
        self.running = []
        self.finished = []
        return done_reqs
