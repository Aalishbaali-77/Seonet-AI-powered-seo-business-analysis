DEFAULT_STAGES = [
    ("new", "New"),
    ("qualified", "Qualified"),
    ("contacted", "Contacted"),
    ("interested", "Interested"),
    ("meeting", "Meeting"),
    ("proposal", "Proposal"),
    ("negotiation", "Negotiation"),
    ("won", "Won"),
    ("lost", "Lost"),
]


def seed_pipeline_stages(pipeline) -> None:
    from apps.crm.models import Stage

    if pipeline.stages.exists():
        return
    for index, (code, name) in enumerate(DEFAULT_STAGES):
        Stage.objects.get_or_create(
            tenant=pipeline.tenant,
            pipeline=pipeline,
            code=code,
            defaults={"name": name, "order": index, "is_won": code == "won", "is_lost": code == "lost"},
        )


def ensure_default_pipeline(tenant):
    from apps.crm.models import Pipeline

    pipeline, created = Pipeline.objects.get_or_create(tenant=tenant, is_default=True, defaults={"name": "Sales"})
    if created or not pipeline.stages.exists():
        seed_pipeline_stages(pipeline)
    return pipeline
