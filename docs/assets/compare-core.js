(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.TorchletCompareCore = api;
})(typeof globalThis === "undefined" ? this : globalThis, function () {
  "use strict";

  function splitLines(code) {
    if (code === undefined) {
      return [];
    }
    if (code === "") {
      return [""];
    }
    return code.endsWith("\n") ? code.slice(0, -1).split("\n") : code.split("\n");
  }

  function buildOperations(baseLines, targetLines) {
    const baseLength = baseLines.length;
    const targetLength = targetLines.length;
    const commonLengths = Array.from({ length: baseLength + 1 }, () =>
      Array(targetLength + 1).fill(0)
    );

    for (let baseIndex = baseLength - 1; baseIndex >= 0; baseIndex -= 1) {
      for (let targetIndex = targetLength - 1; targetIndex >= 0; targetIndex -= 1) {
        commonLengths[baseIndex][targetIndex] =
          baseLines[baseIndex] === targetLines[targetIndex]
            ? commonLengths[baseIndex + 1][targetIndex + 1] + 1
            : Math.max(
                commonLengths[baseIndex + 1][targetIndex],
                commonLengths[baseIndex][targetIndex + 1]
              );
      }
    }

    const operations = [];
    let baseIndex = 0;
    let targetIndex = 0;
    while (baseIndex < baseLength && targetIndex < targetLength) {
      if (baseLines[baseIndex] === targetLines[targetIndex]) {
        operations.push({
          kind: "equal",
          baseNo: baseIndex + 1,
          targetNo: targetIndex + 1,
          baseText: baseLines[baseIndex],
          targetText: targetLines[targetIndex],
        });
        baseIndex += 1;
        targetIndex += 1;
      } else if (
        commonLengths[baseIndex + 1][targetIndex] >=
        commonLengths[baseIndex][targetIndex + 1]
      ) {
        operations.push({
          kind: "delete",
          baseNo: baseIndex + 1,
          baseText: baseLines[baseIndex],
        });
        baseIndex += 1;
      } else {
        operations.push({
          kind: "add",
          targetNo: targetIndex + 1,
          targetText: targetLines[targetIndex],
        });
        targetIndex += 1;
      }
    }

    while (baseIndex < baseLength) {
      operations.push({
        kind: "delete",
        baseNo: baseIndex + 1,
        baseText: baseLines[baseIndex],
      });
      baseIndex += 1;
    }
    while (targetIndex < targetLength) {
      operations.push({
        kind: "add",
        targetNo: targetIndex + 1,
        targetText: targetLines[targetIndex],
      });
      targetIndex += 1;
    }
    return operations;
  }

  function buildRows(baseCode, targetCode) {
    const operations = buildOperations(splitLines(baseCode), splitLines(targetCode));
    const rows = [];
    let added = 0;
    let deleted = 0;
    let index = 0;

    while (index < operations.length) {
      const operation = operations[index];
      if (operation.kind === "equal") {
        rows.push(operation);
        index += 1;
        continue;
      }

      const deletes = [];
      const additions = [];
      while (index < operations.length && operations[index].kind !== "equal") {
        if (operations[index].kind === "delete") {
          deletes.push(operations[index]);
        } else {
          additions.push(operations[index]);
        }
        index += 1;
      }

      deleted += deletes.length;
      added += additions.length;
      const changedRows = Math.max(deletes.length, additions.length);
      for (let offset = 0; offset < changedRows; offset += 1) {
        const base = deletes[offset];
        const target = additions[offset];
        if (base && target) {
          rows.push({
            kind: "change",
            baseNo: base.baseNo,
            targetNo: target.targetNo,
            baseText: base.baseText,
            targetText: target.targetText,
          });
        } else {
          rows.push(base || target);
        }
      }
    }
    return { rows, added, deleted };
  }

  function splitTokens(text) {
    return text.match(/\s+|[A-Za-z_]\w*|\d+(?:\.\d+)?|./gu) || [];
  }

  function mergeSegments(segments) {
    const merged = [];
    for (const segment of segments) {
      const previous = merged[merged.length - 1];
      if (previous && previous.changed === segment.changed) {
        previous.text += segment.text;
      } else {
        merged.push({ ...segment });
      }
    }
    return merged;
  }

  function diffSegments(baseText, targetText) {
    const baseTokens = splitTokens(baseText);
    const targetTokens = splitTokens(targetText);
    const commonLengths = Array.from({ length: baseTokens.length + 1 }, () =>
      Array(targetTokens.length + 1).fill(0)
    );

    for (let baseIndex = baseTokens.length - 1; baseIndex >= 0; baseIndex -= 1) {
      for (
        let targetIndex = targetTokens.length - 1;
        targetIndex >= 0;
        targetIndex -= 1
      ) {
        commonLengths[baseIndex][targetIndex] =
          baseTokens[baseIndex] === targetTokens[targetIndex]
            ? commonLengths[baseIndex + 1][targetIndex + 1] + 1
            : Math.max(
                commonLengths[baseIndex + 1][targetIndex],
                commonLengths[baseIndex][targetIndex + 1]
              );
      }
    }

    const baseSegments = [];
    const targetSegments = [];
    let baseIndex = 0;
    let targetIndex = 0;
    while (baseIndex < baseTokens.length && targetIndex < targetTokens.length) {
      if (baseTokens[baseIndex] === targetTokens[targetIndex]) {
        const text = baseTokens[baseIndex];
        baseSegments.push({ text, changed: false });
        targetSegments.push({ text, changed: false });
        baseIndex += 1;
        targetIndex += 1;
      } else if (
        commonLengths[baseIndex + 1][targetIndex] >=
        commonLengths[baseIndex][targetIndex + 1]
      ) {
        baseSegments.push({ text: baseTokens[baseIndex], changed: true });
        baseIndex += 1;
      } else {
        targetSegments.push({ text: targetTokens[targetIndex], changed: true });
        targetIndex += 1;
      }
    }
    while (baseIndex < baseTokens.length) {
      baseSegments.push({ text: baseTokens[baseIndex], changed: true });
      baseIndex += 1;
    }
    while (targetIndex < targetTokens.length) {
      targetSegments.push({ text: targetTokens[targetIndex], changed: true });
      targetIndex += 1;
    }
    return {
      baseSegments: mergeSegments(baseSegments),
      targetSegments: mergeSegments(targetSegments),
    };
  }

  function addHunks(rows) {
    const hunks = [];
    let activeHunk = null;
    rows.forEach((row, rowIndex) => {
      row.rowIndex = rowIndex;
      if (row.kind === "equal") {
        activeHunk = null;
        return;
      }
      if (!activeHunk) {
        activeHunk = {
          index: hunks.length,
          startRow: rowIndex,
          endRow: rowIndex,
        };
        hunks.push(activeHunk);
      } else {
        activeHunk.endRow = rowIndex;
      }
      row.hunkIndex = activeHunk.index;
    });
    return hunks;
  }

  function foldUnchangedRows(rows, contextLines, hunks) {
    if (hunks.length === 0) {
      return rows;
    }
    const visible = Array(rows.length).fill(false);
    for (const hunk of hunks) {
      const first = Math.max(0, hunk.startRow - contextLines);
      const last = Math.min(rows.length - 1, hunk.endRow + contextLines);
      for (let index = first; index <= last; index += 1) {
        visible[index] = true;
      }
    }

    const displayRows = [];
    let index = 0;
    while (index < rows.length) {
      if (visible[index]) {
        displayRows.push(rows[index]);
        index += 1;
        continue;
      }
      const start = index;
      while (index < rows.length && !visible[index]) {
        index += 1;
      }
      displayRows.push({
        kind: "fold",
        id: `fold-${start}-${index - 1}`,
        startRow: start,
        endRow: index - 1,
        count: index - start,
      });
    }
    return displayRows;
  }

  function diffFile(baseCode, targetCode, options = {}) {
    const contextLines = options.contextLines ?? 3;
    const diff = buildRows(baseCode, targetCode);
    for (const row of diff.rows) {
      if (row.kind === "change") {
        Object.assign(row, diffSegments(row.baseText, row.targetText));
      }
    }
    const hunks = addHunks(diff.rows);
    return {
      ...diff,
      hunks,
      displayRows: foldUnchangedRows(diff.rows, contextLines, hunks),
    };
  }

  function compareFile(path, baseCode, targetCode) {
    const diff = diffFile(baseCode, targetCode);
    let status = "modified";
    if (baseCode === undefined) {
      status = "added";
    } else if (targetCode === undefined) {
      status = "deleted";
    } else if (baseCode === targetCode) {
      status = "unchanged";
    }
    return { path, status, ...diff };
  }

  function compareVersions(payload, baseId, targetId) {
    const versionIds = payload.versions.map((version) => version.id);
    const baseIndex = versionIds.indexOf(baseId);
    const targetIndex = versionIds.indexOf(targetId);
    if (baseIndex === -1 || targetIndex === -1 || targetIndex <= baseIndex) {
      throw new Error("Target Version must be later than Base Version");
    }

    const baseFiles = payload.code[baseId] || {};
    const targetFiles = payload.code[targetId] || {};
    const paths = Array.from(
      new Set([...Object.keys(baseFiles), ...Object.keys(targetFiles)])
    ).sort();
    const files = paths.map((path) =>
      compareFile(path, baseFiles[path], targetFiles[path])
    );
    const changedFiles = files.filter((file) => file.status !== "unchanged");
    return {
      baseId,
      targetId,
      files,
      summary: {
        changedFiles: changedFiles.length,
        added: files.reduce((total, file) => total + file.added, 0),
        deleted: files.reduce((total, file) => total + file.deleted, 0),
      },
    };
  }

  function chooseDefaultFile(comparison, preferredPath, requestedPath) {
    const requested = comparison.files.find((file) => file.path === requestedPath);
    if (requested) {
      return requested;
    }
    const preferred = comparison.files.find(
      (file) => file.path === preferredPath && file.status !== "unchanged"
    );
    if (preferred) {
      return preferred;
    }
    const changedFiles = comparison.files
      .filter((file) => file.status !== "unchanged")
      .sort(
        (left, right) =>
          right.added + right.deleted - (left.added + left.deleted) ||
          left.path.localeCompare(right.path)
      );
    return changedFiles[0] || comparison.files[0] || null;
  }

  function laterVersions(payload, baseId) {
    const baseIndex = payload.versions.findIndex((version) => version.id === baseId);
    return baseIndex === -1 ? [] : payload.versions.slice(baseIndex + 1);
  }

  function resolveVersionPair(payload, requestedBaseId, requestedTargetId) {
    if (payload.versions.length < 2) {
      throw new Error("At least two implemented Versions are required");
    }
    const requestedTargets = laterVersions(payload, requestedBaseId);
    if (requestedTargets.some((version) => version.id === requestedTargetId)) {
      return { baseId: requestedBaseId, targetId: requestedTargetId };
    }
    return {
      baseId: payload.versions[0].id,
      targetId: payload.versions[1].id,
    };
  }

  return {
    buildRows,
    chooseDefaultFile,
    compareVersions,
    diffFile,
    laterVersions,
    resolveVersionPair,
  };
});
