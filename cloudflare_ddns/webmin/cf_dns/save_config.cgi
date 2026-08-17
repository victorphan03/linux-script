#!/usr/bin/perl
# save_config.cgi - Handle saving or updating domain DDNS config

require './cf_dns-lib.pl';
&ReadParse();

my $old_domain = $in{'old_domain'};
my $email = $in{'AUTH_EMAIL'};
my $key = $in{'AUTH_KEY'};
my $zone = $in{'ZONE_ID'};
my $record = $in{'RECORD_NAME'};
my $proxied = $in{'PROXIED'} eq 'true' ? 'true' : 'false';

if (!$email || !$key || !$zone || !$record) {
    &error("Please fill in all required fields!");
}

my $configs = &get_configs();
my $new_entry = {
    AUTH_EMAIL => $email,
    AUTH_KEY => $key,
    ZONE_ID => $zone,
    RECORD_NAME => $record,
    PROXIED => $proxied
};

my $found = 0;
for (my $i = 0; $i < @$configs; $i++) {
    if ($old_domain && $configs->[$i]->{'RECORD_NAME'} eq $old_domain) {
        $configs->[$i] = $new_entry;
        $found = 1;
        last;
    } elsif (!$old_domain && $configs->[$i]->{'RECORD_NAME'} eq $record) {
        $configs->[$i] = $new_entry;
        $found = 1;
        last;
    }
}

if (!$found) {
    push(@$configs, $new_entry);
}

&save_configs($configs);
&redirect("index.cgi");
