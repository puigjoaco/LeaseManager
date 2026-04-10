from rest_framework import serializers

from core.models import UserScopeAssignment

from .models import User


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class CurrentUserSerializer(serializers.ModelSerializer):
    assignments = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'display_name',
            'default_role_code',
            'assignments',
        )

    def get_assignments(self, obj):
        return [
            {
                'role': assignment.role.code,
                'scope': assignment.scope.code if assignment.scope else None,
                'is_primary': assignment.is_primary,
            }
            for assignment in UserScopeAssignment.objects.select_related('role', 'scope').filter(
                user=obj, effective_to__isnull=True
            )
        ]
