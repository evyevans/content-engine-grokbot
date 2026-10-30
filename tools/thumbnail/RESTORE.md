# Install the thumbnail renderer

From the repository root run:
```sh
bash tools/thumbnail/setup.sh --output-dir .local/my-content/covers
```
This creates `tools/thumbnail/.venv` and installs Pillow/NumPy, then renders a text-only smoke-test cover. Use a Python 3.10+ build with working Pillow color-management support. If your default Python has incompatible packages, invoke a supported interpreter with `--python /path/to/python`.

For optional template-A subject masking, add `--with-mask`. This installs rembg/onnxruntime; first masked render downloads the model. Layout C and `--mask off` do not need it. Layout A automatically falls back when masking is unavailable or unreliable.

```sh
tools/thumbnail/render.sh -t C --headline 'A useful next step' --label 'Project notes' --brand-text 'YOUR BRAND' --out .local/my-content/covers/example.jpg --guides
```
`--brand-text` defaults to blank (no signature); `--no-brand` suppresses even supplied text. Output is a 1080×1920 sRGB JPEG. Use your own real image with `--base` for layouts A/B. The bot adds overlays and grades/crops the original; it never redraws your face or body. Check guides and the final image before delivering. File locations must be accessible on the harness's actual shared computer.
