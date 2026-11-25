from familylab.campaign import prepare, status
from familylab import data
from worker.reference import fingerprint


def main():
    manifest, _ = prepare()
    status('ready', manifest_sha256=fingerprint(manifest), coordinates_per_model=data.COORDINATES,
           broad_configurations_per_model=data.COORDINATES * 5, job_ceiling_per_model=data.JOB_CEILING,
           maximum_configurations_per_model=data.BUDGET_UPPER_BOUND)


if __name__ == '__main__':
    main()
