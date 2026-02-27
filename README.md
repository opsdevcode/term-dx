# term-dx

List and diagnose Kubernetes resources stuck in Terminating state.

## Install

From this directory (e.g. in the Geodesic container or after cloning the repo):

```bash
uv pip install --system .
# or
pip install .
```

The `term-dx` command will be installed to your PATH (e.g. `/usr/local/bin/term-dx`).

## Usage

Set cluster context first (e.g. `set-clus staging`), then run:

```bash
term-dx                        # Find and diagnose all terminating resources
term-dx -l                     # List only (no diagnosis)
term-dx namespace              # Only namespaces
term-dx crd                    # Only CRDs
term-dx pod -n app             # Only pods in namespace app
term-dx namespace my-stuck-ns  # Diagnose a specific namespace
term-dx pod my-pod -n app      # Diagnose a specific pod
term-dx -v                     # Include events (verbose)
```

## Why resources get stuck

- **Finalizers** block deletion until a controller completes cleanup.
- **Namespaces**: dependent resources remain, or API services are unavailable.
- **Pods**: node/container runtime not responding, or finalizers not removed.

The tool prints finalizers, remaining dependents (for namespaces), unavailable API services, and suggested remediation.
