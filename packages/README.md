# Shared packages

The deployable backend remains one Python distribution under `packages/backend/src/insurance_platform`, with explicit `domain`, `application`, `documents`, `synthetic`, `ports`, `security`, `infrastructure`, `observability`, and `delivery` modules. API and worker images are separate delivery artifacts using the same modular core. This avoids premature independently versioned Python packages while preserving dependency boundaries.
