# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta
from django.db import models
from core.utils.services import request_github_issues
from django.contrib.auth.models import User
from celery.decorators import periodic_task

ISSUE_UPDATE_PERIOD = 15 # in minutes


class Region(models.Model):
    """Used to store data for different regions."""
    region_name = models.CharField(max_length=100, unique=True)
    region_image = models.URLField(blank=True)

    class Meta:
        ordering = ('region_name',) # Ascending order according to region name.

    def __str__(self):
        return '%s' % (self.region_name)


class RegionAdmin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    regions = models.ManyToManyField(Region)

    class Meta:
        ordering = ('user',) # Ascending order according to users.


class UserRepo(models.Model):
    """
    UserRepo model is used to store the username and repo-name
    for a repository.
    """
    user = models.CharField(max_length=100)
    repo = models.CharField(max_length=100)
    author = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created',) # Ascending order according to date created.
        unique_together = ("user", "repo", "author") # Avoid repo duplicates.

    def __str__(self):
        return '/%s/%s' % (self.user, self.repo)


class IssueLabel(models.Model):
    """
    Label model for storing labels of an issue.
    """
    label_id = models.IntegerField(primary_key=True)
    label_url = models.URLField()
    label_name = models.CharField(max_length=100)
    label_color = models.CharField(max_length=6)

    class Meta:
        ordering = ('label_name',) # Ascending order according to label_name.


class Issue(models.Model):
    """
    Issue model is used to store github issues.
    """
    # Setting choices for experience needed to solve an issue.
    EASYFIX = 'easyfix'
    MODERATE = 'moderate'
    SENIOR = 'senior'
    EXPERIENCE_NEEDED_CHOICES = (
        (EASYFIX, 'easyfix'),
        (MODERATE, 'moderate'),
        (SENIOR, 'senior'),
    )
    # Model attributes start from here.
    issue_id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=100)
    experience_needed = models.CharField(
        max_length=10,
        choices=EXPERIENCE_NEEDED_CHOICES,
        default=MODERATE,
    )
    expected_time = models.CharField(max_length=100)
    language = models.CharField(max_length=100)
    tech_stack = models.CharField(max_length=100)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    issue_number = models.IntegerField()
    issue_labels = models.ManyToManyField(IssueLabel, blank=True)
    issue_url = models.URLField()
    issue_body = models.TextField()
    regions = models.ManyToManyField(Region)
    
    class Meta:
        ordering = ('updated_at',) # Ascending order according to updated_at.


@periodic_task(run_every=timedelta(minutes=ISSUE_UPDATE_PERIOD), name="periodic_issues_updater")
def periodic_issues_updater():
    """
    Update `Issue` model in the database in every
    `ISSUE_UPDATE_PERIOD` minutes.
    """
    list_of_repos = UserRepo.objects.values('author', 'user', 'repo',)
    for repo in list_of_repos:
        region_queryset = retrive_regions_for_a_user(repo['author'])
        issue_list = request_github_issues(repo['user'], repo['repo'])
        if issue_list['error']:
            print "Error" + str(issue_list['data'])
        else:
            for issue in issue_list['data']:
                validate_and_store_issue(issue, region_queryset)

def retrive_regions_for_a_user(user_id):
    """Fetches all the regions related to a user."""
    region_queryset = Region.objects.filter(regionadmin=user_id)
    return region_queryset

def validate_and_store_issue(issue, region_queryset):
    """
    Validate issue:- if valid - store it into database,
    else - Do not store in database
    """
    if is_issue_state_open(issue):
        if is_issue_valid(issue):
            store_issue_in_db(issue, region_queryset)

def is_issue_state_open(issue):
    """
    Returns true if issue state is open else
    return false and delete the issue from database.
    """
    if issue['state'] == 'open':
        return True
    else:
        delete_closed_issues(issue) # Delete closed issues from db.
        return False

def is_issue_valid(issue):
    """
    Checks if issue is valid for system or not.
    Return True if valid else return false.
    """
    parsed = parse_issue(issue['body'])
    for item in parsed:
        if not item:
            return False # issue is not valid
    print 'Issue with id ' + str(issue['id']) + ' is not valid for our system.'
    return True # issue is valid

def store_issue_in_db(issue, region_queryset):
    """Stores issue in db"""
    experience_needed, language, expected_time, technology_stack = parse_issue(issue['body'])
    experience_needed = experience_needed.strip().lower()
    language = language.strip().lower()
    expected_time = expected_time.strip().lower()
    technology_stack = technology_stack.strip().lower()
    issue_instance = Issue(issue_id=issue['id'], title=issue['title'],
                           experience_needed=experience_needed, expected_time=expected_time,
                           language=language, tech_stack=technology_stack,
                           created_at=issue['created_at'], updated_at=issue['updated_at'],
                           issue_number=issue['number'], issue_url=issue['html_url'],
                           issue_body=issue['body'])
    issue_instance.save()
    for label in issue['labels']:
        label_instance = IssueLabel(label_id=label['id'], label_name=label['name'],
                                    label_url=label['url'], label_color=label['color'])
        label_instance.save()
        issue_instance.issue_labels.add(label_instance)
    issue_instance.regions.add(*region_queryset)

def delete_closed_issues(issue):
    """Delete issues that are closed on GitHub but present in our db"""
    try:
        issue_instance = Issue.objects.get(issue_id=issue['id'])
        issue_instance.delete()
    except Exception:
        print 'Closed issue with id ' + str(issue['id']) + ' is not present is database.'

def parse_issue(issue_body):
    """
    Parse the issue body and return `experience_needed`, `language`,
    `expected_time` and `technology_stack`.
    """
    issue_body = issue_body.lower()
    experience_needed = find_between(issue_body, 'experience', '\r\n')
    language = find_between(issue_body, 'language', '\r\n')
    expected_time = find_between(issue_body, 'expected-time', '\r\n')
    technology_stack = find_between(issue_body, 'technology-stack', '\r\n')
    return experience_needed, language, expected_time, technology_stack

def find_between(string, first, last):
    """
    Return string between two substrings `first` and `last`.
    """
    try:
        start = string.index(first) + len(first)
        end = string.index(last, start)
        return string[start:end].replace(': ', '')
    except ValueError:
        return ""
