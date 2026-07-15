from torch import Tensor
from .kvcache import KVCache
from dataclasses import dataclass


@dataclass
class ForwardParams:
    req_indptr_cpu: Tensor
    position_index: Tensor
    slot_ids_cpu: None | list[int]
    active_mask: None | Tensor
    is_prefill: bool
    kvcache: KVCache
    block_table: Tensor
