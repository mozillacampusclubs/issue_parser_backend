from rest_framework import serializers
from core.models import UserRepo, Issue, IssueLabel, Region


class UserRepoSerializer(serializers.ModelSerializer):
    """
    Serializer for `UserRepo` Model.
    """
    class Meta:
        model = UserRepo
        fields = ('id', 'user', 'repo',)


class IssueLabelSerializer(serializers.ModelSerializer):
    """
    Serializer for `IssueLabel` Model.
    """
    class Meta:
        model = IssueLabel
        fields = ('label_id', 'label_name', 'label_color', 'label_url',)


class RegionSerializer(serializers.ModelSerializer):
    """
    Serializer for `Region` Model.
    """
    class Meta:
        model = Region
        fields = ('id','region_name', 'region_image',)


class IssueSerializer(serializers.ModelSerializer):
    """
    Serializer for `Issue` Model.
    """
    issue_labels = IssueLabelSerializer(many=True)

    class Meta:
        model = Issue
        fields = ('issue_id', 'title', 'experience_needed', 'expected_time',
            'language', 'tech_stack', 'created_at', 'updated_at',
            'issue_number', 'issue_labels', 'issue_url', 'issue_body', 'regions',)
