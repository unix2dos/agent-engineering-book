"""验证第 7 课正式正文：临时假文件与本机沙盒，不调用模型或真实业务接口。"""

from contextlib import redirect_stdout
import io
from pathlib import Path
import re
import runpy


def self_check():
    here = Path(__file__).resolve().parent
    chapter = here.parents[1] / "chapters/07-Agent沙盒.md"
    blocks = re.findall(r"```python\n(.*?)\n```", chapter.read_text(encoding="utf-8"), re.S)
    expected = [
        "denied_by_policy\nrejected\nready\n",
        "host_read = True\nsandbox_allowed_read = True\nsandbox_secret_read = False\n",
        "sandbox\nelevation_denied\nhost\n",
    ]
    assert len(blocks) == len(expected)
    namespace = {}
    for block, output in zip(blocks, expected):
        with redirect_stdout(io.StringIO()) as captured:
            # 只执行仓库中的教学代码，不接受模型生成的字符串。
            exec(compile(block, str(chapter), "exec"), namespace)
        assert captured.getvalue() == output, captured.getvalue()

    request = namespace["check_request"]
    backend = namespace["choose_backend"]
    for permitted in (False, True):
        tools = {"read_file"} if permitted else set()
        for approved in (False, True):
            expected_status = "denied_by_policy" if not permitted else "ready" if approved else "rejected"
            assert request("read_file", tools, approved) == expected_status
    for requested in (False, True):
        for allowed in (False, True):
            expected_backend = "sandbox" if not requested else "host" if allowed else "elevation_denied"
            assert backend(requested, allowed) == expected_backend

    safety = runpy.run_path(str(here.parents[1] / "exercises/lesson-07-safety/starter.py"))
    # 复用已有临时目录、权限恢复和回调顺序检查；E 由正文的正反对照替代。
    for checkpoint in ("checkpoint_a", "checkpoint_b", "checkpoint_c", "checkpoint_d", "checkpoint_f"):
        safety[checkpoint]()
    print("lesson 07 passed: policy, approval, backend selection, native sandbox allowed/denied reads")


if __name__ == "__main__":
    self_check()
