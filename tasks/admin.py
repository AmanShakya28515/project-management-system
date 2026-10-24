from django.contrib import admin

# Tasks are deliberately not registered: no admin tooling is in scope, and
# the admin's add form would bypass the app's own creation rules.
