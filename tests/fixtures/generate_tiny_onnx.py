"""Generate the tiny ONNX model committed at tests/fixtures/tiny.onnx.

This is a *documentation / reproducibility* script — it is NOT run in CI and the
`onnx` builder is intentionally not a project dependency. The committed model is
a trivial graph that exercises the OnnxVisionProvider plumbing end-to-end
(decode -> preprocess -> onnxruntime inference -> output mapping); it is not a
trained damage/authenticity model.

Graph: input (1,3,224,224) float32
  -> ReduceMean over spatial axes [2,3]  -> (1,3)
  -> MatMul with a constant (3,2) weight  -> (1,2)   # [damage_logit, synthetic_logit]

Regenerate with:  pip install onnx && python tests/fixtures/generate_tiny_onnx.py
"""

from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

INPUT = helper.make_tensor_value_info(
    "input", TensorProto.FLOAT, [1, 3, 224, 224]
)
OUTPUT = helper.make_tensor_value_info("scores", TensorProto.FLOAT, [1, 2])

# ReduceMean over spatial dims -> (1, 3). Use axes as an attribute (opset 13).
reduce_node = helper.make_node(
    "ReduceMean", ["input"], ["pooled"], axes=[2, 3], keepdims=0
)

# Constant weight (3, 2) mapping channel means to two logits.
weight = numpy_helper.from_array(
    np.array([[0.5, -0.5], [-0.5, 0.5], [0.25, 0.25]], dtype=np.float32),
    name="weight",
)
matmul_node = helper.make_node("MatMul", ["pooled", "weight"], ["scores"])

graph = helper.make_graph(
    [reduce_node, matmul_node],
    "tiny_vision_model",
    [INPUT],
    [OUTPUT],
    initializer=[weight],
)
model = helper.make_model(
    graph, opset_imports=[helper.make_opsetid("", 13)]
)
model.ir_version = 9  # broadly compatible with onnxruntime >= 1.17
onnx.checker.check_model(model)

out_path = Path(__file__).parent / "tiny.onnx"
onnx.save(model, str(out_path))
print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")
