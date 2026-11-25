"""Explicitly authorized sequence; checkpoint revisions never float on restart."""
SPECS = {
    'lfm': {
        'campaign': 'paired-lfm25-350m-v1', 'label': 'LFM2.5-350M',
        'models': {
            'original': ('LiquidAI/LFM2.5-350M', '9921cd4d82c0e3986887aa4b376f9446729ef8a3'),
            'abliterated': ('s3nh/LFM2.5-350M-abliterated', '3b5076fba033be25cb354990e7d03d883cf43b2c'),
        },
        'model_type': 'lfm2', 'layers': 16, 'width': 4608, 'job_ceiling': 420000,
        'seed': 2026112501,
    },
    'granite': {
        'campaign': 'granite40-350m-v1', 'label': 'Granite-4.0-350M',
        'models': {'original': ('ibm-granite/granite-4.0-350m', 'bd8a1497065c0d6ba1ef19af6b0d2b14bacf71c2')},
        'model_type': 'granitemoehybrid', 'layers': 28, 'width': 2048, 'job_ceiling': 350000,
        'seed': 2026112502,
    },
}
