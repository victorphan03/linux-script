#!/usr/bin/perl
# save_stacks.cgi - Save selected Docker Compose stacks for backup

require './homelab-backup-lib.pl';

&ReadParse();

my $cfg = &get_backup_config();
my @selected = split(/\0/, $in{'stacks'});

my $stacks_str = join(',', @selected);
$cfg->{'enabled_stacks'} = $stacks_str;

&save_backup_config($cfg);

&redirect("index.cgi");
