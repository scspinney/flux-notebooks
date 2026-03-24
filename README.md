# flux-notebooks

Running the docker image:

```{bash}
docker run -d --name flux-test \
  -p 8050:8050 \
  -e FLUX_SECRET_KEY='dev-only-secret' \
  -e FLUX_DATASET_ROOT=/datasets/superdemo_real \
  -e FLUX_REDCAP_ROOT=/datasets/redcap \
  -v /home/ubuntu/local_gitlab/flux-notebooks/superdemo_real:/datasets/superdemo_real:ro \
  -v /home/ubuntu/local_gitlab/flux-notebooks/data/redcap:/datasets/redcap:ro \
  flux-notebooks:test-runtime
```
