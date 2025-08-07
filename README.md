# TOPMed Imputation Server CLI Tool

This repo provides utilities to access the TOPMed Imputation Server programmatically.

* `local/api.py` provides `TisV2Api`. Use it to place calls to the Cloudgene3 API.
  * It expects a `data/*.token` file with an access token, where `*` is `dev` or `prod`.
  * You can get a token from the website's UI. Click on your username -> Profile, and enable "API Access". Then copy the token to the appropriate file.
* `script/explore_jwt.py` decodes and pretty-prints the user tokens. They are JWT tokens; there are tools online but this is local and only uses the Python standard library (plus `mff-pretty-cli` for pretty-printing).
* `script/test_endpoints.py` places a few calls to demonstrate and/or test the available endpoints.
  * It expects the test VCF file `data/chr20.R50.merged.1.330k.recode.unphased.small.vcf.gz`, used to submit a light job.
