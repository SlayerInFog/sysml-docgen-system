# Jupyter Demo

本项目已准备一个 JupyterLab 演示环境，用来验证和展示系统接口能力。

## 环境位置

启动脚本会按顺序查找以下位置：

```text
.\.venv\Scripts\jupyter-lab.exe
.\jupyter-env\Scripts\jupyter-lab.exe
..\jupyter-env\Scripts\jupyter-lab.exe
```

如果上述位置都不存在，则使用系统 PATH 中的 `jupyter-lab`。

建议环境中安装：

```text
jupyterlab
ipykernel
requests
pandas
```

## 启动后端

在项目根目录执行：

```powershell
cd .\backend
python run.py
```

## 启动 JupyterLab

在项目根目录执行：

```powershell
.\scripts\start_jupyter.ps1
```

打开：

```text
http://127.0.0.1:8888/lab/tree/notebooks/sysml_docgen_openmbee_demo.ipynb
```

注意：JupyterLab 启动后会一直占用当前 PowerShell 窗口，这是正常现象，不是卡死。使用期间不要关闭这个窗口。

## Notebook 内容

- 调用 `/health` 验证后端运行状态
- 登录系统接口
- 读取项目、模型、模板、文档数据
- 展示 OpenMBEE 适配接口目录
- 上传 `docs/sample-sysml-model.json`
- 查看模型元素和关系
- 使用模板生成文档
