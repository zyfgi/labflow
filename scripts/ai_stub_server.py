"""Minimal OpenAI-compatible stub for local E2E testing.

Usage: python scripts/ai_stub_server.py  (listens on 127.0.0.1:8100)
"""

from fastapi import FastAPI, Request

app = FastAPI()


@app.post("/v1/chat/completions")
async def completions(request: Request) -> dict:
    body = await request.json()
    assert request.headers.get("authorization", "").startswith("Bearer "), "missing key"
    messages = body.get("messages", [])
    last = messages[-1]["content"] if messages else ""
    answer = (
        "根据你当前有权限访问的 LabFlow 数据："
        f"共检索到 {last.count('labflow_source')} 条相关记录，"
        "以下是主要发现（本回答由本地桩模型生成，用于端到端验证）。"
    )
    return {
        "model": body.get("model", "stub"),
        "choices": [{"message": {"role": "assistant", "content": answer}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100, log_level="warning")
