import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '../../../core/services/api.service';
import { ProjectRecruitmentComponent } from './project-recruitment.component';

describe('ProjectRecruitmentComponent creation', () => {
  let apiService: { post: ReturnType<typeof vi.fn>; createAuthHeaders: ReturnType<typeof vi.fn> };
  let snackBar: { open: ReturnType<typeof vi.fn> };
  let component: ProjectRecruitmentComponent;

  beforeEach(() => {
    apiService = {
      post: vi.fn(),
      createAuthHeaders: vi.fn(() => ({}))
    };
    snackBar = { open: vi.fn() };
    const translate = { instant: vi.fn((key: string) => key) };
    component = new ProjectRecruitmentComponent(
      apiService as unknown as ApiService,
      translate as unknown as TranslateService,
      snackBar as unknown as MatSnackBar
    );
    component.form.title = 'Recruit contributors';
    component.form.summary = 'Build the next release.';
  });

  it('blocks creation and shows a snackbar when the repository URL is missing', () => {
    component.form.title = '';

    component.createProject();

    expect(apiService.post).not.toHaveBeenCalled();
    expect(snackBar.open).toHaveBeenCalledWith(
      'privateRecruit.feedback.githubUrlRequired',
      'privateRecruit.actions.dismiss',
      expect.objectContaining({ panelClass: ['studio-snackbar', 'studio-snackbar-error'] })
    );
  });

  it('blocks creation and shows a snackbar for a non-repository URL', () => {
    component.form.github_url = 'https://github.com/example';

    component.createProject();

    expect(apiService.post).not.toHaveBeenCalled();
    expect(snackBar.open).toHaveBeenCalledWith(
      'privateRecruit.feedback.githubUrlInvalid',
      'privateRecruit.actions.dismiss',
      expect.any(Object)
    );
  });

  it('submits the selected contact method and valid GitHub repository URL', () => {
    component.form.contact = 'discord';
    component.form.github_url = 'https://github.com/example/project';
    apiService.post.mockReturnValue(of({
      id: 1,
      title: component.form.title,
      summary: component.form.summary,
      contact: component.form.contact,
      github_url: component.form.github_url,
      review_status: 'open',
      creator: { id: 1, username: 'leader' },
      members: [],
      member_count: 0,
      joined_by_me: false,
      owned_by_me: true
    }));

    component.createProject();

    expect(apiService.post).toHaveBeenCalledWith(
      '/project-recruitments',
      expect.objectContaining({
        contact: 'discord',
        github_url: 'https://github.com/example/project'
      }),
      {}
    );
    expect(component.form.github_url).toBe('');
  });
});
