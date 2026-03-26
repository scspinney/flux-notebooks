# Flux Notebooks Dashboard

This guide covers the current auth flow and deployment commands.

- Auth mode: local JSON users file
- Access policy: pre-approved usernames only
- First sign-up: user sets their real password once on `/auth/signup`

## 0. Python environment setup (`requirements.txt`)

```bash
cd /home/ubuntu/local_gitlab/flux-notebooks
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

After activation, use `python` in the commands below.

## 1. Where user credentials live

Use a persistent path, not `/tmp`.

- Local/dev: `/home/ubuntu/local_gitlab/flux-notebooks/.flux_users.json`
- Container in compose/swarm (recommended): `/state/.flux_users.json` via `dashboard-state:/state`

`/tmp` is only for throwaway testing.

## 2. Manage users (pre-approve + list + reset)

From repo root:

```bash
cd /home/ubuntu/local_gitlab/flux-notebooks
```

Pre-approve a user for first sign-up:

```bash
python scripts/manage_users.py --users-file ./.flux_users.json approve alice
```

Seed a password directly (optional, bypasses signup page):

```bash
python scripts/manage_users.py --users-file ./.flux_users.json add alice --password 'StrongPassword123!'
```

Reset existing password:

```bash
python scripts/manage_users.py --users-file ./.flux_users.json set-password alice --password 'NewStrongPassword123!'
```

List users and status:

```bash
python scripts/manage_users.py --users-file ./.flux_users.json list
```

## 3. Run locally (no Docker)

```bash
cd /home/ubuntu/local_gitlab/flux-notebooks
FLUX_USERS_FILE=/home/ubuntu/local_gitlab/flux-notebooks/.flux_users.json \
FLUX_SECRET_KEY='dev-secret-change-me' \
python app.py
```

Open:

- `http://localhost:8050/auth`

If app runs on a remote host, tunnel:

```bash
ssh -N -L 28050:localhost:8050 ubuntu@<server-host>
```

Then open:

- `http://localhost:28050/auth`

## 4. Build Docker image

```bash
cd /home/ubuntu/local_gitlab/flux-notebooks
docker build --pull -t flux-notebooks:test-runtime .
```

## 5. Run one container with persistent user state

Use a host state directory that persists across restarts.

```bash
mkdir -p /home/ubuntu/flux-notebooks/dashboard-state
sudo chown -R 10001:10001 /home/ubuntu/flux-notebooks/dashboard-state
```

Run container:

```bash
docker rm -f flux-test 2>/dev/null || true

docker run -d --name flux-test \
  -p 8050:8050 \
  -e FLUX_SECRET_KEY='change-this-in-prod' \
  -e FLUX_USERS_FILE=/state/.flux_users.json \
  -e FLUX_DATASET_ROOT=/datasets/superdemo_real \
  -e FLUX_REDCAP_ROOT=/datasets/redcap \
  -v /home/ubuntu/local_gitlab/flux-notebooks/superdemo_real:/datasets/superdemo_real:ro \
  -v /home/ubuntu/local_gitlab/flux-notebooks/data/redcap:/datasets/redcap:ro \
  -v /home/ubuntu/flux-notebooks/dashboard-state:/state \
  flux-notebooks:test-runtime
```

Verify:

```bash
docker ps --filter name=flux-test --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker logs --tail=120 flux-test
curl -i http://localhost:8050/auth
```

## 6. Manage users in running container

```bash
docker exec -it flux-test python /app/scripts/manage_users.py --users-file /state/.flux_users.json approve alice
docker exec -it flux-test python /app/scripts/manage_users.py --users-file /state/.flux_users.json list
```

## 7. Deploy with Docker Swarm / compose stack (Arbutus example)

From this repo:

```bash
export DOMAIN=<your-domain>
docker build --pull -t flux-notebooks:test-runtime .
docker stack deploy -c docker-compose.dashboard.wip.yml dashboard
```

Check stack:

```bash
docker stack services dashboard
docker stack ps dashboard
```

Manage users in deployed service (inside container):

```bash
CONTAINER="$(docker ps --filter name=dashboard_dashboard --format '{{.Names}}' | head -n1)"
docker exec -it "$CONTAINER" python /app/scripts/manage_users.py --users-file /state/.flux_users.json list
docker exec -it "$CONTAINER" python /app/scripts/manage_users.py --users-file /state/.flux_users.json approve alice
```

## 8. Auth flow summary for end users

1. User opens `/auth`
2. If first-time approved user: click `Activate account` and set password on `/auth/signup`
3. User signs in on `/auth`

## 9. Cleanup

Stop one-container run:

```bash
docker rm -f flux-test
```

Optional image cleanup:

```bash
docker rmi flux-notebooks:test-runtime
```

## Notes

- The assistant/chat feature is disabled in this build path.
- Container includes `git` and `git-annex` for DataLad-based dataset operations.
- For production, inject `FLUX_SECRET_KEY` via secret management (not hardcoded).
