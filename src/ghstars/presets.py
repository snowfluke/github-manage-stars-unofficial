"""The built-in 32 default categories.

These are deliberately broad and tuned for typical developer accounts.
You can override completely by passing your own JSON file — see examples/.
"""
from __future__ import annotations

from .categorize import Category

DEFAULT_CATEGORIES: list[Category] = [
    Category(
        name="Archived",
        description="Repos marked archived on GitHub — stale, consider unstar",
        patterns=[],
    ),
    Category(
        name="Claude & Anthropic Tooling",
        description="Claude Code, Claude API, MCP, Anthropic SDK, agent skills",
        patterns=[
            r"\bclaude\b", r"\banthropic\b", r"\bmcp\b",
            r"claude-code", r"claude_code", r"model-context-protocol", r"opencode",
        ],
    ),
    Category(
        name="AI Agents & Orchestration",
        description="Agent frameworks, multi-agent systems, agentic workflows",
        patterns=[
            r"\bagent\b", r"\bagents\b", r"agentic",
            r"autogen", r"crewai", r"langchain", r"langgraph", r"\bautogpt\b",
        ],
    ),
    Category(
        name="LLM Inference & Serving",
        description="Local LLM runners, inference engines, model serving, prompt frameworks",
        patterns=[
            r"llama\.cpp", r"llama-cpp", r"\bollama\b", r"\bvllm\b",
            r"\bllm\b", r"\bllms\b", r"inference", r"gguf", r"quantization",
            r"text-generation", r"language-model", r"\bgpt-?\d", r"transformers?\b",
            r"prompt-engineering", r"structured-outputs?", r"outlines",
        ],
    ),
    Category(
        name="Fine-tuning & Training",
        description="Model fine-tuning, training frameworks, datasets",
        patterns=[
            r"fine-?tuning", r"\bunsloth\b", r"\btraining\b",
            r"\blora\b", r"\bsft\b", r"\brlhf\b", r"\bpeft\b", r"deepspeed",
        ],
    ),
    Category(
        name="RAG & Vector Search",
        description="Retrieval-augmented generation, vector search, embeddings",
        patterns=[
            r"\brag\b", r"retrieval-augmented", r"vector-?search",
            r"\bembeddings?\b", r"\bweaviate\b", r"colbert", r"semantic-search",
        ],
    ),
    Category(
        name="OCR & Document AI",
        description="OCR engines, document layout, receipt / invoice parsing",
        patterns=[
            r"\bocr\b", r"paddleocr", r"tesseract", r"\bsurya\b",
            r"docling", r"document-ai", r"layout-?parser", r"textract",
            r"cv-parser", r"document.image", r"scene.text", r"dewarping", r"rectification",
        ],
    ),
    Category(
        name="Computer Vision",
        description="OpenCV, segmentation, object detection, face / tracking, vision models",
        patterns=[
            r"\bopencv\b", r"computer-vision", r"image-processing", r"image-classification",
            r"image-captioning", r"\byolo\b", r"yolov?\d", r"\bsam\b", r"segmentation",
            r"object-detection", r"\bvision\b", r"detectron",
            r"face-detection", r"face-recognition", r"face-analysis",
            r"multi-object-tracking", r"bytetrack", r"controlnet",
            r"\bdiffusion\b", r"stable-diffusion", r"super-resolution",
            r"\bdalle\b", r"dall.?e", r"image-generation",
        ],
    ),
    Category(
        name="TTS, ASR & Audio AI",
        description="Text-to-speech, speech recognition, voice cloning, audio models",
        patterns=[
            r"\btts\b", r"text-to-speech", r"\basr\b", r"speech-?recognition",
            r"speech-?synthesis", r"\bsynthesis\b", r"\bvoice\b", r"voice-cloning",
            r"\bwhisper\b", r"\baudio\b", r"speech-?api",
        ],
    ),
    Category(
        name="PDF & Document Processing",
        description="PDF parsing, rendering, manipulation",
        patterns=[r"\bpdf\b", r"mupdf", r"pdfjs", r"pdf-?lib"],
    ),
    Category(
        name="Hono & Edge Web",
        description="Hono framework, edge runtimes, Cloudflare Workers",
        patterns=[r"\bhono\b", r"cloudflare-workers", r"\bworkers\b.*edge", r"\bedge\b"],
    ),
    Category(
        name="Bun Ecosystem",
        description="Bun-specific tools, runtimes, libraries",
        patterns=[r"\bbun\b"],
    ),
    Category(
        name="React & Next.js",
        description="React libraries, Next.js, React-based UI",
        patterns=[r"\breact\b", r"nextjs", r"next\.js", r"\brsc\b"],
    ),
    Category(
        name="Vue / Nuxt",
        description="Vue ecosystem",
        patterns=[r"\bvue\b", r"\bnuxt\b"],
    ),
    Category(
        name="Solid / Svelte / Other Frontend",
        description="SolidJS, Svelte, Astro, alternative frontend frameworks",
        patterns=[
            r"\bsolid\b", r"solidjs", r"\bsvelte\b", r"\bastro\b", r"\bqwik\b",
        ],
    ),
    Category(
        name="UI Components & Design Systems",
        description="Component libraries, design systems, headless UI",
        patterns=[
            r"shadcn", r"\bui-?kit\b", r"design-system", r"component-library",
            r"\bui\b.*components", r"radix", r"headless-?ui",
        ],
    ),
    Category(
        name="Editors & Rich Text",
        description="Code editors, rich text / WYSIWYG, markdown editors, e-readers, notes",
        patterns=[
            r"\beditor\b", r"\btiptap\b", r"prosemirror", r"slate\b", r"ckeditor",
            r"\blexical\b", r"\bcodemirror\b", r"\bmonaco\b", r"wysiwyg", r"rich-?text",
            r"\bebook-?reader\b", r"\bepub\b", r"\bobsidian\b", r"note-?taking",
            r"\blibrum\b", r"\bfoliate\b",
        ],
    ),
    Category(
        name="Mobile (Android / iOS / RN)",
        description="Android, iOS, React Native, Expo, Kotlin",
        patterns=[
            r"\bandroid\b", r"\bios\b", r"react-?native", r"\bexpo\b",
            r"\bkotlin\b", r"\bswift\b",
        ],
    ),
    Category(
        name="Rust Ecosystem",
        description="Rust libraries and tools",
        patterns=[],
        language="rust",
    ),
    Category(
        name="CLI & Developer Tools",
        description="Terminal tools, CLI utilities, browser extensions, dev productivity",
        patterns=[
            r"\bcli\b", r"command-line", r"\btui\b", r"terminal", r"developer-tools",
            r"\bdotfiles\b",
            r"browser-extension", r"chrome-extension", r"firefox-extension", r"webextension",
        ],
    ),
    Category(
        name="DevOps & Infra",
        description="Docker, Kubernetes, CI / CD, deployment",
        patterns=[
            r"\bdocker\b", r"\bkubernetes\b", r"\bk8s\b", r"\bci/cd\b", r"\bdevops\b",
            r"\bhelm\b", r"terraform",
        ],
    ),
    Category(
        name="Self-hosted & Open SaaS",
        description="Self-hostable apps, open-source alternatives to SaaS",
        patterns=[r"self-?hosted", r"\bself-?host\b", r"open-source-alternative"],
    ),
    Category(
        name="Databases & ORMs",
        description="Databases, ORMs, query builders",
        patterns=[
            r"\bdatabase\b", r"\bpostgres\b", r"\bsqlite\b", r"\bmongodb\b",
            r"\bredis\b", r"\borm\b", r"drizzle", r"prisma", r"kysely",
        ],
    ),
    Category(
        name="API Tooling & OpenAPI",
        description="API frameworks, OpenAPI, REST / GraphQL tooling",
        patterns=[
            r"openapi", r"\bswagger\b", r"\bscalar\b", r"graphql",
            r"rest-?api", r"\btrpc\b",
        ],
    ),
    Category(
        name="Image / Video / Graphics",
        description="Canvas, WebGL, image manipulation (non-AI), WASM media libs",
        patterns=[
            r"\bcanvas\b", r"\bwebgl\b", r"\bthree\.js\b", r"\bvideo\b",
            r"\bgraphics\b", r"\bsvg\b", r"\bglsl\b", r"animation",
            r"\bwasm\b", r"webassembly", r"emscripten",
        ],
    ),
    Category(
        name="Scraping, Bots & Anti-Detection",
        description="Scrapers, headless browsers, anti-bot bypass, captcha solvers, chat bots",
        patterns=[
            r"scrap(?:er|ing|y)", r"\bpuppeteer\b", r"playwright", r"patchright",
            r"\bselenium\b", r"\bcaptcha\b", r"turnstile", r"cloudflare-?bypass",
            r"anti-?bot", r"anti-?detect", r"fingerprint", r"botasaurus",
            r"\bbot\b", r"automation.*browser", r"undetected",
            r"\bwhatsapp\b", r"\bbaileys\b", r"\bwaha\b", r"wwebjs",
            r"\btelegram\b", r"\bdiscord\b", r"chat-?bot", r"\bchatbot\b",
        ],
    ),
    Category(
        name="Security & Pentesting",
        description="Pentesting tools, OSINT, security auditing, infosec",
        patterns=[
            r"penetration-?testing", r"pentest", r"\binfosec\b", r"\bosint\b",
            r"\bhacking\b", r"\bcybersecurity\b", r"security-audit", r"\bsecurity\b",
            r"\brce\b", r"\bxss\b", r"\bcsrf\b", r"reverse-?engineering",
            r"frida", r"\bspoof\b",
        ],
    ),
    Category(
        name="Desktop & OS Customization",
        description="macOS / Linux / Windows theming, Hackintosh, status bars, themes",
        patterns=[
            r"\bhackintosh\b", r"\bmacos\b.*(?:theme|customization|bar)",
            r"sketchybar", r"\bryzen\b", r"\bwsl\b", r"\bgnome\b", r"\bkde\b",
            r"\bxfce\b", r"firefox-?theme", r"gtk-?theme", r"userchrome",
            r"\bdesktop-environment\b", r"\bstatusbar\b", r"\bopencore\b",
        ],
    ),
    Category(
        name="Languages & Compilers",
        description="Language implementations, compilers, parsers",
        patterns=[
            r"programming-?language", r"\bcompiler\b", r"\binterpreter\b",
            r"\bquickjs\b", r"\bv8\b", r"language.*compiler",
        ],
    ),
    Category(
        name="Compression & Encoding",
        description="Compression algorithms, codecs, encoders",
        patterns=[
            r"\bcompression\b", r"\bcodec\b", r"\blz4\b", r"\bzstd\b",
            r"\bbrotli\b", r"\bsquoosh\b", r"image.*compress",
        ],
    ),
    Category(
        name="Learning Resources",
        description="Awesome lists, tutorials, courses, books",
        patterns=[
            r"\bawesome\b", r"\btutorial\b", r"\bcourse\b", r"\bbook\b",
            r"\blearning\b", r"\bcheatsheet\b", r"\broadmap\b", r"interview",
        ],
    ),
    Category(
        name="Other",
        description="Repos that did not match any rule — review manually",
        patterns=[],
    ),
]


assert len(DEFAULT_CATEGORIES) <= 32, (
    f"Default presets must fit GitHub's 32-list cap "
    f"(got {len(DEFAULT_CATEGORIES)} categories)."
)
