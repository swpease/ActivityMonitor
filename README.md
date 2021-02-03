# ActivityMonitor
Puts `top` command output into a sqlite db.

I made this script to have some unique time series data to toy with. Note that the default datetime output from `top` is not parseable by SQLite. I did not do anything about this, so if you want to play with SQLite's datetime functionality, you'll have to reformat the `top` datetimes to SQLite datetimes.
