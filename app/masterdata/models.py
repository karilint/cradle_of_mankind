from django.db import models
from django.db.models.deletion import CASCADE, SET_NULL, PROTECT, RESTRICT

from users.models import User
from tasks.models import Task


class Source(models.Model):
    def name_based_upload(instance, filename):
        return "source_files/{}/{}".format(instance.name, filename)

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default="")
    reference = models.TextField(blank=True, default="")
    source_file = models.FileField(upload_to=name_based_upload)
    delimiter = models.CharField(max_length=10)
    master_created = models.BooleanField(default=False)
    masterdata_stage = models.IntegerField(default=0)
    masterdata_rules = models.TextField(null=True, default=None)

    class Meta:
        default_related_name = "sources"


class SourceEntity(models.Model):
    source = models.ForeignKey(Source, on_delete=CASCADE)
    source_key = models.CharField(max_length=255, null=True, default=None)

    class Meta:
        default_related_name = "source_entities"


class SourceField(models.Model):
    name = models.CharField(max_length=255)
    is_primary_key = models.BooleanField(default=False)
    display_order = models.IntegerField()
    source = models.ForeignKey(Source, on_delete=CASCADE)
    is_divided = models.BooleanField(default=False)
    delimiters = models.CharField(max_length=255, blank=True, default="")
    num_of_parts = models.IntegerField(default=1)
    num_of_mappings = models.IntegerField(default=1)

    class Meta:
        default_related_name = "source_fields"
        ordering = ["display_order"]


class SourceData(models.Model):
    value = models.ForeignKey("Value", null=True, on_delete=PROTECT)
    source_entity = models.ForeignKey(SourceEntity, on_delete=CASCADE)
    source_field = models.ForeignKey(SourceField, on_delete=CASCADE)

    class Meta:
        default_related_name = "source_datas"


class MasterEntity(models.Model):
    master_key = models.CharField(max_length=255)
    hidden_key = models.IntegerField(default=None, null=True)

    class Meta:
        default_related_name = "master_entities"
        ordering = ["master_key"]


class MasterField(models.Model):
    class AccessLevels(models.IntegerChoices):
        GUEST = 1
        REGISTERED = 2
        EDITOR = 3
        DATA_ADMIN = 4

    name = models.CharField(max_length=255, unique=True)
    abbreviation = models.CharField(max_length=255, blank=True, default="")
    primary_key = models.BooleanField(default=False)
    display_order = models.IntegerField(default=1)
    hidden = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    access_level = models.IntegerField(
        choices=AccessLevels.choices, default=AccessLevels.GUEST
    )

    class Meta:
        default_related_name = "master_fields"
        ordering = ["display_order"]


class MasterData(models.Model):
    value = models.ForeignKey("Value", null=True, on_delete=PROTECT)
    master_entity = models.ForeignKey(MasterEntity, on_delete=CASCADE)
    master_field = models.ForeignKey(MasterField, on_delete=CASCADE)
    source_datas = models.ManyToManyField(
        SourceData,
        through="MasterSourceData",
    )

    class Meta:
        default_related_name = "master_datas"


class MasterSourceData(models.Model):
    source_data = models.ForeignKey(SourceData, on_delete=CASCADE)
    master_data = models.ForeignKey(MasterData, on_delete=CASCADE)


class Value(models.Model):
    value = models.TextField()

    class Meta:
        default_related_name = "values"


class EditComment(models.Model):
    text = models.TextField(blank=True)
    prev_value = models.ForeignKey(
        Value, on_delete=PROTECT, related_name="prev_value_comments"
    )
    new_value = models.ForeignKey(
        Value, on_delete=PROTECT, related_name="new_value_comments"
    )
    date = models.DateTimeField(auto_now_add=True)
    master_data = models.ForeignKey(MasterData, on_delete=CASCADE)
    user = models.ForeignKey(User, on_delete=SET_NULL, null=True)

    class Meta:
        default_related_name = "edit_comments"


class Export(models.Model):
    class ExportType(models.TextChoices):
        CSV = "csv"

    class Status(models.IntegerChoices):
        PENDING = 1
        IN_PROGRESS = 2
        DONE = 3

    class MatchingType(models.TextChoices):
        EXACT = "exact"
        CONTAINS = "contains"
        STARTS_WITH = "startswith"
        ENDS_WITH = "endswith"

    file = models.FileField(
        upload_to="exports/", blank=True, null=True, default=None
    )
    references = models.FileField(
        upload_to="references/", blank=True, null=True, default=None
    )
    file_type = models.CharField(
        max_length=3,
        choices=ExportType.choices,
        default=ExportType.CSV,
    )
    status = models.IntegerField(
        choices=Status.choices,
        default=Status.PENDING,
    )
    task = models.OneToOneField(Task, on_delete=SET_NULL, null=True)
    user = models.ForeignKey(User, null=True, on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    search = models.CharField(max_length=255, blank=True)
    matching = models.CharField(
        max_length=10,
        choices=MatchingType.choices,
    )
    case_sensitive = models.BooleanField()
