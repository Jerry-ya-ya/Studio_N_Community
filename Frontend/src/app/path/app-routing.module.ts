import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
//AppPath
import { appPath } from '../path/app-path-const'; // Adjust the import path as necessary

const routes: Routes = [
  {
    path: '',
    redirectTo: appPath.home,
    pathMatch: 'full',
  },
  {
    path: appPath.home,
    loadChildren: () =>
      import('../pages/public/home/home.module').then(m => m.HomeModule),
  },
  {
    path: appPath.crawler,
    loadChildren: () =>
      import('../pages/private/crawler/crawler.module').then(m => m.CrawlerModule),
  },
  {
    path: appPath.login,
    loadChildren: () =>
      import('../pages/public/login/login/login.module').then(m => m.LoginModule)
  },
  {
    path: appPath.member,
    loadChildren: () =>
      import('../pages/public/member/member.module').then(m => m.MemberModule)
  },
  {
    path: appPath.profile,
    loadChildren: () =>
      import('../pages/private/profile/profile.module').then(m => m.ProfileModule)
  },
  {
    path: appPath.register,
    loadChildren: () =>
      import('../pages/public/register/register/register.module').then(m => m.RegisterModule)
  },
  {
    path: appPath.setting,
    loadChildren: () =>
      import('../pages/private/setting/setting.module').then(m => m.SettingModule)
  },
  {
    path: appPath.square,
    loadChildren: () =>
      import('../pages/private/square/square.module').then(m => m.SquareModule)
  },
  { 
    path: appPath.todo,
    loadChildren: () =>
      import('../pages/private/todo/todo.module').then(m => m.TodoModule)
  },
  {
    path: appPath.checkIn,
    loadChildren: () =>
      import('../pages/private/check-in/check-in.module').then(m => m.CheckInModule)
  },
  {
    path: appPath.schedule,
    loadChildren: () =>
      import('../pages/private/schedule/schedule.module').then(m => m.ScheduleModule)
  },
  {
    path: appPath.promote,
    loadChildren: () =>
      import('../pages/superadmin/promote/promote.module').then(m => m.PromoteModule)
  },
  {
    path: appPath.superadminLogs,
    loadChildren: () =>
      import('../pages/superadmin/logs/logs.module').then(m => m.LogsModule)
  },
  {
    path: appPath.content,
    loadChildren: () =>
      import('../pages/admin/content/content.module').then(m => m.ContentModule)
  },
  {
    path: appPath.projects,
    loadChildren: () =>
      import('../pages/admin/projects/projects.module').then(m => m.ProjectsModule)
  },
  {
    path: appPath.activity,
    loadChildren: () =>
      import('../pages/admin/activity/activity.module').then(m => m.ActivityModule)
  },
  {
    path: appPath.adminLogs,
    loadChildren: () =>
      import('../pages/admin/logs/logs.module').then(m => m.LogsModule)
  },
  {
    path: appPath.friend,
    loadChildren: () =>
      import('../pages/private/friend/friend.module').then(m => m.FriendModule)
  },
  {
    path: appPath.projectRecruitment,
    loadChildren: () =>
      import('../pages/private/project-recruitment/project-recruitment.module').then(m => m.ProjectRecruitmentModule)
  },
  {
    path: appPath.post,
    loadChildren: () =>
      import('../pages/private/post/post.module').then(m => m.PostModule)
  },
  {
    path: appPath.aboutwebsite,
    loadChildren: () =>
      import('../pages/public/aboutwebsite/aboutwebsite.module').then(m => m.AboutwebsiteModule)
  },
  {
    path: appPath.userhome,
    loadChildren: () =>
      import('../pages/private/userhome/userhome.module').then(m => m.UserhomeModule)
  },
  {
    path: appPath.tutorial,
    loadChildren: () =>
      import('../pages/public/tutorial/tutorial.module').then(m => m.TutorialModule)
  },
  {
    path: appPath.update,
    loadChildren: () =>
      import('../pages/public/update/update.module').then(m => m.UpdateModule)
  },
  {
    path: appPath.publicActivities,
    loadChildren: () =>
      import('../pages/public/activities/activities.module').then(m => m.ActivitiesModule)
  },
  {
    path: appPath.privateActivities,
    loadChildren: () =>
      import('../pages/private/activities/activities.module').then(m => m.ActivitiesModule)
  },
  {
    path: '**',
    redirectTo: '',
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
