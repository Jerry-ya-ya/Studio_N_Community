import { inject } from '@angular/core';
import { CanMatchFn, Router } from '@angular/router';

import { appPath } from '../../path/app-path-const';


export const adminGuard: CanMatchFn = () => {
  const role = localStorage.getItem('role');
  if (role === 'admin' || role === 'superadmin') {
    return true;
  }

  return inject(Router).createUrlTree([appPath.home]);
};
