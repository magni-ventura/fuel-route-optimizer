from rest_framework import serializers


class FuelRouteRequestSerializer(serializers.Serializer):
    start_location = serializers.CharField(
        max_length=255
    )
    finish_location = serializers.CharField(
        max_length=255
    )

    def validate(self, attrs):
        start = attrs["start_location"].strip()
        finish = attrs["finish_location"].strip()

        if not start or not finish:
            raise serializers.ValidationError(
                "Start and finish locations are required."
            )

        if start.casefold() == finish.casefold():
            raise serializers.ValidationError(
                "Start and finish locations must differ."
            )

        attrs["start_location"] = start
        attrs["finish_location"] = finish

        return attrs