import { inject } from '@angular/core';
import { CanMatchFn, Router } from '@angular/router';

import { appPath } from '../../path/app-path-const';

export const superadminGuard: CanMatchFn = () => {
  if (localStorage.getItem('role') === 'superadmin') {
    return true;
  }

  return inject(Router).createUrlTree([appPath.home]);
};
