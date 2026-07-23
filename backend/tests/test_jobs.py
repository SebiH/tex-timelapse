"""Unit tests for tex_timelapse.api.jobs.JobManager - the in-process render job
registry backing the async job API."""

import pytest

from tex_timelapse.api.jobs import JobManager, JobStatus


def test_create_returns_running_job_with_unique_id():
    mgr = JobManager()
    a = mgr.create('proj-a', 'out')
    b = mgr.create('proj-b', 'out')
    assert a.status == JobStatus.RUNNING
    assert a.id != b.id
    assert mgr.get(a.id) is a


def test_second_concurrent_job_for_same_project_is_rejected():
    mgr = JobManager()
    mgr.create('proj', 'out')
    with pytest.raises(RuntimeError, match='already running'):
        mgr.create('proj', 'out')


def test_finishing_a_job_frees_the_project_slot():
    mgr = JobManager()
    first = mgr.create('proj', 'out')
    mgr.finish(first.id, JobStatus.COMPLETED)
    assert mgr.get(first.id).status == JobStatus.COMPLETED
    # a new render for the same project may now start
    second = mgr.create('proj', 'out')
    assert second.id != first.id
    assert second.status == JobStatus.RUNNING


def test_different_projects_run_concurrently():
    mgr = JobManager()
    mgr.create('a', 'out')
    # not the same project -> allowed
    mgr.create('b', 'out')


def test_cancel_flag_is_recorded():
    mgr = JobManager()
    job = mgr.create('proj', 'out')
    assert job.cancel_requested is False
    job.request_cancel()
    assert job.cancel_requested is True


def test_get_unknown_job_is_none():
    assert JobManager().get('nope') is None


def test_finish_unknown_job_is_a_noop():
    # must not raise
    JobManager().finish('nope', JobStatus.FAILED, 'boom')
