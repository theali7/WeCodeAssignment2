# Recovered published WeCode frontend

Publication: https://wecode-design-preview.alishchatik.chatgpt.site/
Initial browser capture: 2026-11-02. This directory serves the captured JavaScript/CSS, technology icons and five Gilroy font weights. The entrypoint was reconstructed without the hosting editor widget. Older editable code remains under src/ and is not the Docker UI build input.

## Source and runtime recovery

The saved Sites source repository became accessible in the later Linux environment. Source commit 7bab7f837f32a537ad691e99af5b5c719f37205b contains the full source tree under source/ and the matching publication under dist/. Its main bundle index-DXabLyQE.js has SHA-256 be0b4df9432c2a679f8e6144ee59826b069c509b45099234222014a9310b8989, identical to this captured bundle. The full editable frontend has not yet replaced the older src/ in this assignment.

Runtime workers, shared helpers, TeaVM loader and notices are restored from source/public/runtimes. Large Python/SQL/Java dependencies are reconstructed at Docker build time from public upstream distributions, with every archive and selected file pinned by SHA-256 in scripts/runtime-manifest.json. All 34 assembled runtime files were compared with the saved source and matched byte-for-byte. No access token is required or stored in the assignment image or repository.

The single application Dockerfile now serves this frontend through FastAPI together with an isolated PostgreSQL account API. Its runtime copy is patched to the same-origin /api; the captured bundle in Git stays unchanged. The existing connect-src 'self' CSP prevents browser requests to production Supabase. Runtime assets use the same origin. See DOCKER_SETUP.md for startup, limitations and validation. The previous Nginx preview/source-preview Docker targets no longer apply.

Gilroy-Black.ttf exists in the saved Sites source but is not included in this initial five-weight font capture. Full pixel equivalence is not claimed. The Problems catalogue contains 108 problems. Fourteen core Playwright scenarios and the separate real-runtime/topic suite define browser verification; check Actions for their actual result. The original hosted site, GitHub repository and production database are unchanged by this assignment work.
