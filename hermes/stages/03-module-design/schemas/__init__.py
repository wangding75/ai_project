"""
Hermes 模块接口 Schema 定义（接口真相源头）

本包中的每个 .py 文件对应一个业务模块，定义：
  - Request/Response Pydantic model
  - 错误码类（<Module>Errors）

阶段 04 TDD 测试必须从这里 import 模型，任何实现代码也必须 import 这里的类型，
不得自定义 dataclass 重复定义接口。

非功能性约束见 slo.yaml。
"""
