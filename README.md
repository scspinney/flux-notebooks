# Flux Notebooks Dashboard: Docker Build & Run

This guide covers building and running the dashboard container using the current production Docker setup (`Dockerfile` + `requirements.runtime.txt`).

## 1. Prerequisites

- Docker installed on the host
- Dataset paths available on host:
  - BIDS dataset root (example: `/home/ubuntu/local_gitlab/flux-notebooks/superdemo_real`)
  - REDCap data root (example: `/home/ubuntu/local_gitlab/flux-notebooks/data/redcap`)

## 2. Build the image

```bash
cd /home/ubuntu/local_gitlab/flux-notebooks
docker build --pull -t flux-notebooks:test-runtime .
```

## 3. Run the container

```bash
docker rm -f flux-test 2>/dev/null || true

docker run -d --name flux-test \
  -p 8050:8050 \
  -e FLUX_SECRET_KEY='change-this-in-prod' \
  -e FLUX_DATASET_ROOT=/datasets/superdemo_real \
  -e FLUX_REDCAP_ROOT=/datasets/redcap \
  -v /home/ubuntu/local_gitlab/flux-notebooks/superdemo_real:/datasets/superdemo_real:ro \
  -v /home/ubuntu/local_gitlab/flux-notebooks/data/redcap:/datasets/redcap:ro \
  flux-notebooks:test-runtime
```

## 4. Verify startup

```bash
docker ps --filter name=flux-test --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker logs --tail=120 flux-test
curl -i http://localhost:8050/auth
```

Expected:
- container status becomes `healthy`
- `/auth` returns `HTTP/1.1 200 OK`

## 5. Access from your browser

If you are on the same machine:
- `http://localhost:8050/auth`

If app runs on remote server:
- direct access: `http://<server-host>:8050/auth` (if network/firewall allows it)
- or SSH tunnel:
  ```bash
  ssh -N -L 28050:localhost:8050 ubuntu@<server-host>
  ```
  then open:
  - `http://localhost:28050/auth`

## 6. Stop and clean up

```bash
docker rm -f flux-test
```

Optional cleanup image:
```bash
docker rmi flux-notebooks:test-runtime
```

## 7. Common issues

- `Bind for 0.0.0.0:8050 failed: port is already allocated`
  - Another service is using `8050`; use a different host port (example `-p 18050:8050`).

- `curl: (7) Failed to connect`
  - Container likely exited; check:
  ```bash
  docker ps -a --filter name=flux-test
  docker logs flux-test
  ```

## Notes

- The assistant/chat feature is disabled in this build path.
- Container includes `git` and `git-annex` for DataLad-based dataset operations.
- For production, inject `FLUX_SECRET_KEY` via secret management (not hardcoded).
