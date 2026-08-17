#!/usr/bin/perl
# api.cgi - AJAX endpoint for tunnel_management Webmin module

require './tunnel_management-lib.pl';
use JSON::PP;

&ReadParse();

print "Content-type: application/json\n\n";

my $action = $in{'action'};
my %params;

foreach my $k (keys %in) {
    next if $k eq 'action';
    $params{$k} = $in{$k};
}

my $res = &run_python_cmd($action, \%params);

print encode_json($res);
