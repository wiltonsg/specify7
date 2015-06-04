from django.conf.urls import url
from django.conf import settings

if settings.ATTACHMENT_MODULE == 'idigbio':
    from specifyweb.idigbio_media_gw.views import get_settings as attachment_settings
else:
    from specifyweb.attachment_gw.views import get_settings as attachment_settings

from specifyweb.report_runner.views import get_status as report_runner_status
from . import views

urlpatterns = [
    url(r'^login/$', views.api_login),
    url(r'^collection/$', views.collection),
    url(r'^user.json$', views.user),
    url(r'^system_info.json$', views.system_info),
    url(r'^domain.json$', views.domain),
    url(r'^view.json$', views.view),
    url(r'^datamodel.json$', views.datamodel),
    url(r'^schema_localization.json$', views.schema_localization),
    url(r'^app.resource$', views.app_resource),
    url(r'^available_related_searches.json$', views.available_related_searches),
    url(r'^remoteprefs.properties$', views.remote_prefs),

    url(r'^attachment_settings.json$', attachment_settings),
    url(r'^report_runner_status.json$', report_runner_status),
]
