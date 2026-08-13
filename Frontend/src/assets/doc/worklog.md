# jackandbeanstalk #

<h1 style="color:gold;"> V1 </h1>

## 2025/06/09 ##

- Set up the website architecture.

## 2025/06/11 ##

- Set up routing to implement SPA navigation and add a crawler page.

- 💥 Didn't change branches before developing. Now there’s a huge conflict mess.

- Text and artwork for the homepage.

- Text and artwork for the loginpage and minor homepage adjustments.

- 💥 Due to unknown reasons, some files reverted to their original version. I need to restore the previous commit from GitHub.

- Text and artwork for the memberpage and added nav for memberpage.

- 💥 Can't select the input blocks and button of loginpage.

- Text and artwork for the register page. Complete the register component. Add some decorate.

## 2025/06/12 ##

- Rebase all the branch to branch Jerry.

- 🔧 Fix the bug ID:1 and the animations of title box in memberpage.

## 2025/06/13 ##

- Complete the Login page and create the forgotpasswordpage for it.
    (routerLink should add '/' for root-level redirection)

- Complete the login and logout feature, turn some navbar to private and connect SQL.

- Complete the todo feature, create an interceptor, and inject it.

- Complete the profile feature with editable email, nickname, and avatar.

## 2025/06/14 ##

- Complete the Usersquarepage.

- Complete the change password feature in setting page.

- Complete the crawler for Hacker News and schedule it to run every 15 minutes.

## 2025/06/16 ##

- Complete the email verification when registering an account.

<h1 style="color:gold;"> V2 </h1>

## 2025/06/16 ##

- Dockerlize the whole project and switch Microsoft SQL to PostgreSQL.

- 💥 Nginx often returns a 404 error, and users need to re-enter the URL to get redirected to the homepage.

- Create and adjust the Nginx configuration.

## 2025/06/21 ##

- Architecture design supporting multi-mode Docker configuration, successfully building a dual-container system for both development and deployment environments.

## 2025/06/22 ##

- Implement README and Todo documents.

- Implement a feature to resend the verification email using Gmail.

## 2025/06/23 ##

- Restructure the project by linking subpages to the main page, and organizing subpage components under the main page’s folder. Separate the crawler logs from Python application logs.

- 💥 The root cause appears to be blocking or concurrent execution of scheduled threads, leading to missed jobs.

- 🔧 Fix thread blocking issues and implemented proper exception handling to improve stability.

- 💥 The current crawler process freezes after approximately five runs. To resolve this, we plan to migrate the task scheduling to Celery for more reliable asynchronous execution.

## 2025/06/24 ##

- 💥 Platform incompatibility with native binaries was caused by lock files and node_modules created on Windows. To resolve this, remove the lock files and node_modules, allowing Docker to perform a clean installation during the build process.

- Implement Playwright support along with a dedicated container to perform end-to-end testing of Angular content and interactive UI components.

## 2025/06/28 ##

- 💥 Docker consumes too much memory, so the user configured .wslconfig settings.

- 💥 The memory limit set for Docker was too low and no swap was configured, causing the disk usage to spike to 100%.

## 2025/06/29 ##

- Organize the project, environments, and related .yml configurations to support three stages: development, testing, and deployment.

- Completed Playwright automation for verifying the registration feature and facilitating future tests of post-login functionalities. Additionally, exposed a test API on the backend for the test environment.

## 2025/06/30 ##

- 💥 Playwright is unable to properly load components and data that require login access

## 2025/07/02 ##

- 💥 Playwright is currently unable to connect to the Angular container, so automated tests are temporarily executed on the local machine instead.

- Refactored the structure to separate Playwright from the Angular frontend.

## 2025/07/03 ##

- Adjusted the photos on the team members page and cleaned up the images in the public directory.

- Implemented super admin and admin functionalities, updated the .env file, and revised Playwright test functions.

## 2025/07/04 ##

- Implemented role checks for admin and super admin, and added a dedicated navbar for them.

## 2025/07/06 ##

- Refactored the frontend structure and implemented an admin promotion feature for the super admin.

## 2025/07/07 ##

- Implemented a feature that allows the super admin to demote an admin.

- 💥 The .yml failed to load the .env from the env folder during container build, so the .env was moved to the project root.

- 💥 Changed the exposed port of the Docker container’s database to avoid conflicts with the local database.

## 2025/07/08 ##

- Implemented a Redis container, updated the YAML file, and moved the .env file back to the project root directory.

- Implemented a Celery container.

- 💥 Changing user roles caused the query results to become unordered, so a sorting rule was implemented on the backend to maintain consistent order.

## 2025/07/13 ##

- Connected Celery with Redis to enable Celery Beat to schedule and execute tasks.

## 2025/07/14 ##

- Improved the visual design of the navbar, implemented responsive layout for various screen sizes, enhanced color contrast, and updated the logout button with a red color for better visibility.

- Improved the design of the registration page.

## 2025/07/15 ##

- Redesigned the navbar into a hamburger menu for better responsiveness, adjusted the layout of the Single Page Application and navbar, and applied CSS refinements to various pages.

## 2025/07/16 ##

- Improved the visual design of the user square, refined the member page’s CSS, resolved image rendering issues on the promote page, and made layout adjustments to the navbar for better consistency.

## 2025/07/17 ##

- Improved the design of the user profile and fixed CSS issues on several pages.

- Improved the design of the user's Todo List page.

<h1 style="color:gold;"> V3 </h1>

- Implemented a feature that allows users to add friends.

## 2025/07/18 ##

- Implemented a feature that allows users to delete friends.

- 💥 Fixed an issue where the public navbar would disappear when the user did not have super admin privileges.

- Implemented the functionality to send, accept, and remove friend requests.

## 2025/07/21 ##

- Implemented the functionality to enter a user's public page by clicking on their name, and improved the design of the friends page.

## 2025/08/15 ##

- Trying to pulled images from Docker Hub to Microsoft Azure containers.

## 2025/08/16 ##

- Go through setbacks and hardships.

## 2025/08/17 ##

- Go through setbacks and hardships.

## 2025/08/18 ##

- 💥 Removed dependency on prod.yml, added a health check for Angular, and modified the Nginx configuration.

- Successfully pulled the Angular image from Docker Hub to a Microsoft Azure container and deployed it with HTTPS enabled.

## 2025/08/19 ##

- 💥 Added a health check route for Flask and modified the database connection logic to prevent the app from shutting down on failure.

- Successfully pulled Flask from Docker Hub into a Microsoft Azure container and connected it to a PostgreSQL database.

## 2025/08/20 ##

- 💥 Fixed all hardcoded API URLs in the frontend and corrected the allowed HTTP methods.

- Made most features functional after deployment to Azure, except for the scheduled crawler.

## 2025/08/21 ##

- 💥 Each query requires reconnecting to the database, resulting in the need to re-establish the connection before every session, which negatively impacts user experience.

- Connection Pooling the PostgreSQL database and updated the .env.example file.

- Created and improved the design of the website introduction page.

- Improved the design of the Member page.

## 2025/08/22 ##
- Improved the design of the Resendverification page.

- Created and improved the design of the post-wall page.

## 2025/08/23 ##

- 💥 The API for fetching GitHub repository data is causing users to be forcibly logged out. To avoid triggering the logout logic, a new HTTP client without interceptors was created.

- Created and improved the design of the userhome page. Added the user creation time to the user cards on the Square page.

## 2025/08/25 ##

- 💥 Installing the package causes the navbar and multiple other packages to malfunction.

- Repackaged the Angular project and upgraded the version from 19.2.14 to 20.2.0 to resolve the package installation issue.

## 2025/08/26 ##

- 💥 In Angular 20, the new version outputs the build files into the browser subdirectory instead of directly under dist/frontend. Updated the Dockerfile to correctly copy the files.

- Created and improved the design of the tutorial page. Update content on the About page.

## 2025/08/27 ##

- Update content on the Home page and Tutorial page.

- Implemented the functionality to edit and delete posts.

- Update content on the Home page.

## 2026/03/03 ##

- Refactored the backend structure to centralize route management, and fixed an issue where the super admin could not be correctly identified during registration.

## 2026/03/03 ##

- Implemented backend test scripts with pytest to the testing environment, and separated the development, testing, and production environment groups.

## 2026/03/16 ##

- Implemented startup, shutdown, pause, and rebuild scripts for the three application environments.

## 2026/03/17 ##

- Implemented pytest tests for the user registration feature.

- Centralized backend environment management by consolidating environment variable files into a single file.

- Update content on the README.md page.

## 2026/03/18 ##

- Update angular kits and angular kits update steps part in README.md.

## 2026/03/20 ##

- Implemented pytest tests for the superadmin registration feature and the registration email sending feature.

<h1 style="color:gold;"> V4 </h1>

## 2026/07/03 ##

- Fix backend admin checks and update frontend images.

- Harden backend auth identity and request validation.

- Fix profile email validation, post pagination, and production config.

- Redesign the CMENStudio homepage.

## 2026/07/04

- Add timed EDEN and CMENStudio theme switching.

- Add themed community news and polish the navigation menu.

- Refine homepage news cards with glass overlays.

- Unify the Angular pages with the shared studio theme.

- Unify Angular themes and redesign the member directory.

- Modernize the WPA tutorial page.

- Modernize the registration page.

- Modernize the login page.

## 2026/07/05

- Modernize private settings and fix friend page background.

- Modernize the private profile page.

- Modernize the private crawler page.

## 2026/07/08

- Fix missing todo route in Docker deployment.

## 2026/07/09

- Improve theme contrast and add the ouroboros day-night control.

- Add friend actions to the square page.

- Improve square page readability and remove fake like counts.

## 2026/07/10

- Add project recruitment pages and APIs.

## 2026/07/11

- Add recruitment management tools.

## 2026/07/12

- Add project todo dispatch for recruitment teams.

- Group project todos and refresh the todo page.

- Improve login redirect and friend request refresh.

- Add fallback avatars to the square page.

## 2026/07/14

- Add todo priority and Alembic migrations.

- Add fallback avatars to private post pages.

- Improve logout navigation and login autofill.

- Upgrade Angular frontend from 20 to 21.

## 2026/07/15

- Upgrade Angular frontend from 21 to 22.

- Add admin homepage news content management.

- Improve admin content responsive layout.

## 2026/07/16

- Normalize backend timestamps to UTC+8.

- Add public update worklog page.

## 2026/07/17

- Reverse update timeline and stabilize todo project groups.

## 2026/07/18

- Add todo claim ownership workflow.

- Reduce post page CSS budget usage.

- Add homepage i18n with a global language dropdown.

- Add i18n translations to the hamburger menu.

- Add Japanese and Korean i18n support.

- Add i18n to global controls and update the frontend build image.

## 2026/07/19

- Add i18n support to the members page.

- Add i18n support to the about page.

- Add i18n support to the tutorial page.

- Add i18n support to the update page.

- Add i18n support to the register page.

- Add i18n support to the login page.

- Add i18n support to the private home page.

## 2026/07/20

- Add i18n support to the private post wall.

- Add i18n support to the private square page.

- Add i18n support to the private recruitment page.

- Add i18n support to the private friend page.

- Add i18n support to the private todo page.

- Add i18n support to the private setting page.

- Add i18n support to the private profile page.

- Add i18n support to the private crawler page.

- Add i18n support to the admin content page.

## 2026/07/21

- Add Angular Material snackbar notifications to the login page.

- Replace session expiration alerts with snackbar notifications.

- Unify frontend styling with the Eden Night theme.

- Add logout success snackbar notifications.

## 2026/07/22

- Add a site theme controller to settings.

- Fix external API 401 logout by scoping auth interception.

## 2026/07/23

- Add admin-managed public member content with GitHub URLs.

- Add member avatars and fixed member roles.

- Sync admin member editor scrolling.

## 2026/07/24

- Show registered users as public members with profile GitHub URLs.

- Combine project todo publishing and management cards.

## 2026/07/29

- Optimize content scrolling and todo summary layout.

- Restyle post wall without emoji decorations.

- Add home news background image management.

- Lock world cycling by default and align login register link.

- Replace world toggle with logo mode switch and cycle control.

- Redesign sidebar navigation as an icon rail.

- Separate app shell layout from sidebar rail.

- Float top controls and align public home hero.

- Use rotating cycle icon for world automation.

## 2026/07/30

- Fix sidebar rail icon sizing with collapsed scrollbars.

- Add sidebar brand wordmark home entry.

- Align top controls with sidebar toggle.

- Add daily check-in rewards with immediate UI updates.

- Add seven-day check-in progress card.

## 2026/08/01

- Add superadmin point totals and split user list layout.

- Apply brand fonts to the public home hero.

- Add admin project recruitment overview page.

## 2026/08/02

- Add admin project todo details to recruitment overview.

- Add profile avatar source preference.

## 2026/08/03

- Fix friend avatars and member profile linking.

- Add todo claim completion gates and effort levels.

- Align todo level controls and defaults.

## 2026/08/04

- Add project completion review workflow.

## 2026/08/05

- Update todo priority multiplier controls.

- Move settlement requests to todo projects.

- Update todo review groups and persist sidebar state.

- Refine todo completion review flow.

## 2026/08/06

- Add recurring todo settlement cycles.

## 2026/08/07

- Unify page surfaces and improve scroll performance.

## 2026/08/08

- Add black and white site themes.

- Improve private profile and crawler responsive layouts.

## 2026/08/09

- Add more site themes and refine setting layout.

- Add admin activity management page.

- Connect admin activity management to backend.

- Fix activity refresh and responsive recruit layout.

## 2026/08/10

- Refactor setting and activity hero cards.
## 2026/08/11

- Improve browser credential support for login.

## 2026/08/13

- Add remember me refresh tokens and register credentials support.

- Add private home post hearts.
