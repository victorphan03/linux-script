#!/usr/bin/perl
# save_cron.cgi - Save Cron schedule settings

require './homelab-backup-lib.pl';

&ReadParse();

my $cfg = &get_backup_config();
$cfg->{'cron_enable'} = $in{'cron_enable'};
$cfg->{'cron_schedule'} = $in{'cron_schedule'};

&save_backup_config($cfg);

&redirect("index.cgi");
