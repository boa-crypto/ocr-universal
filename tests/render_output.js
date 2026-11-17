"use strict";
function validateRenderOutput(output, expected) {
  const lines = output.split("\n").filter(line => /\[OK\]|\[KO\]|\[FAIL\]/.test(line));
  if (/\[(?:KO|FAIL|THROW|REJET|NON GERE)\]/.test(output) || lines.length !== expected)
    throw new Error(`${lines.length}/${expected} contrôles de rendu valides attendus\n${output}`);
  return lines.length;
}
module.exports = {validateRenderOutput};
