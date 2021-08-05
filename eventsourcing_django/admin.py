from django.contrib import admin

from .models import StoredEventRecord, SnapshotRecord, NotificationTrackingRecord

admin.site.register(StoredEventRecord)
admin.site.register(SnapshotRecord)
admin.site.register(NotificationTrackingRecord)
