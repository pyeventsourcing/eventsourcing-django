# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import NotificationTrackingRecord, SnapshotRecord, StoredEventRecord

admin.site.register(StoredEventRecord)
admin.site.register(SnapshotRecord)
admin.site.register(NotificationTrackingRecord)
