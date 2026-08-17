#!/usr/bin/perl
# save_settings.cgi - Save global interval settings

require './cf_dns-lib.pl';
&ReadParse();

my $interval = int($in{'interval'});
if ($interval < 10) {
    $interval = 10;
}

my $settings = &get_settings();
$settings->{'interval'} = $interval;

&save_settings($settings);
&redirect("index.cgi");
