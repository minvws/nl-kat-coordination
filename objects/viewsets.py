from rest_framework.request import Request
from rest_framework.viewsets import ViewSet
from structlog import get_logger

logger = get_logger(__name__)


class ObjectViewSet(ViewSet):
    def list(self, request, *args, **kwargs):
        # TODO: fix
        pass
        # if "object_type" in request.GET:
        #     q = Query(type_by_name(request.GET["object_type"]))
        # else:
        #     q = Query()
        #
        # for parameter in request.GET:
        #     if parameter == "object_type":
        #         continue
        #
        #     if parameter == "offset":
        #         q = q.offset(int(request.GET.get(parameter)))
        #         continue
        #     if parameter == "limit":
        #         q = q.limit(int(request.GET.get(parameter)))
        #         continue
        #
        #     value = list(set(request.GET.getlist(parameter)))
        #
        #     if len(value) == 1:
        #         try:
        #             q = q.where(q.result_type, **{parameter: value[0]})
        #         except InvalidField:
        #             logger.debug("Invalid field for query", result_type=q.result_type, parameter=parameter)
        #     elif len(value) > 1:
        #         try:
        #             q = q.where_in(q.result_type, **{parameter: value})
        #         except InvalidField:
        #             logger.debug("Invalid field for query", result_type=q.result_type, parameter=parameter)
        #             continue
        #
        # # TODO
        # organization = Organization.objects.first()
        # connector: OctopoesAPIConnector = settings.OCTOPOES_FACTORY(organization.code)
        #
        # oois = connector.octopoes.ooi_repository.query(q, datetime.now(timezone.utc))
        # serializer = ObjectSerializer(oois, many=True)
        #
        # return Response({"results": serializer.data, "next": None, "previous": None, "count": None})

    def create(self, request: Request, *args, **kwargs):
        # TODO: fix
        pass
    def delete(self, request: Request, *args, **kwargs):
        # TODO: fix
        pass
