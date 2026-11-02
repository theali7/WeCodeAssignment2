# Recovered published WeCode frontend

Source: https://wecode-design-preview.alishchatik.chatgpt.site/
Captured on 2026-11-02 using the owner-authorized browser.

This directory contains browser-delivered production JavaScript/CSS, technology icons and five loaded Gilroy fonts. This is a recovered frontend build, not the original React/TypeScript source. The older editable code remains under src/; changing it does not change this preview.

Recovered: main application, Problems, shared problem data, LearnLanguages, LearningWay, and all stylesheets in the main application's dependency map. index.html is a reconstructed minimal entrypoint. The hosting editor widget is excluded.

Docker Compose's preview target now serves this directory. The source-preview target builds the older source separately. The existing CSP blocks external connections, so local signup/login and remote learning-data operations are disabled until an isolated backend is implemented. No production database or hosted-site changes were made.

The stylesheet also references Gilroy-Black.ttf, which was not observed or recovered. Five other loaded weights are included. Full visual/functional equivalence has not been established. The original site was inspected after owner login: its Problems list shows 108 problems and its Learn Languages and Learning Way navigation loads the corresponding modules.

Validation: local JavaScript syntax and relative module/dependency graph checks. Docker build/run still requires a working daemon connection; do not treat this frontend recovery as completing assignment issues #2-#4.
