#!/usr/bin/perl
# fetch_options.cgi - Fetch Accounts, Tunnels, and Zones from Cloudflare API

require './tunnel_management-lib.pl';
&ReadParse();

my $api_token = $in{'api_token'};
my $account_id = $in{'account_id'};
my $tunnel_id = $in{'tunnel_id'};
my $zone_id = $in{'zone_id'};

if (!$api_token) {
    &error("Please enter a Cloudflare API Token first!");
}

my $acc_res = &run_python_cmd('fetch_accounts', { api_token => $api_token });
my $tun_res = &run_python_cmd('fetch_tunnels', { api_token => $api_token, account_id => $account_id });
my $zone_res = &run_python_cmd('fetch_zones', { api_token => $api_token });

&ui_print_header(undef, "Select Cloudflare Account, Tunnel & Zone", "", undef, 0, 0);

print &ui_form_start("save_config.cgi", "post");
print &ui_hidden("api_token", $api_token);

print &ui_table_start("Cloudflare Resources Found", "width=100%", 2);

# 1. Accounts Dropdown
my @acc_opts;
if ($acc_res->{'status'} && @{$acc_res->{'msg'}}) {
    foreach my $acc (@{$acc_res->{'msg'}}) {
        push(@acc_opts, [ $acc->{'id'}, "$acc->{'name'} ($acc->{'id'})" ]);
    }
}
if (!@acc_opts) {
    push(@acc_opts, [ $account_id, $account_id ]) if $account_id;
}
print &ui_table_row("Select Account", &ui_select("account_id", $account_id || ($acc_opts[0] ? $acc_opts[0]->[0] : ''), \@acc_opts));

# 2. Tunnels Dropdown
my @tun_opts;
if ($tun_res->{'status'} && @{$tun_res->{'msg'}}) {
    foreach my $t (@{$tun_res->{'msg'}}) {
        my $st = $t->{'status'} ? " [$t->{'status'}]" : "";
        push(@tun_opts, [ $t->{'id'}, "$t->{'name'}$st ($t->{'id'})" ]);
    }
}
if (!@tun_opts) {
    push(@tun_opts, [ $tunnel_id, $tunnel_id ]) if $tunnel_id;
}
print &ui_table_row("Select Tunnel", &ui_select("tunnel_id", $tunnel_id || ($tun_opts[0] ? $tun_opts[0]->[0] : ''), \@tun_opts));

# 3. Zones Dropdown
my @zone_opts = ([ "", "-- None / Manual --" ]);
if ($zone_res->{'status'} && @{$zone_res->{'msg'}}) {
    foreach my $z (@{$zone_res->{'msg'}}) {
        push(@zone_opts, [ $z->{'id'}, "$z->{'name'} ($z->{'id'})" ]);
    }
}
print &ui_table_row("Select Zone (Optional)", &ui_select("zone_id", $zone_id, \@zone_opts));

print &ui_table_end();
print &ui_form_end([ [ undef, "Confirm & Save Configuration" ] ]);

&ui_print_footer("index.cgi", "Return to Module Main");
