#!/usr/bin/perl
# index.cgi - Main Dashboard for Homelab Backup 3-2-1-1-0 Webmin Module

require './homelab-backup-lib.pl';
&ui_print_header(undef, "Homelab Backup 3-2-1-1-0", "", undef, 1, 1);

my $cfg = &get_backup_config();
my $running = &is_backup_running();
my $summary = &get_last_backup_summary();
my $stacks = &discover_docker_compose_stacks($cfg->{'local_src'});

# Parse enabled stacks configuration
my %enabled_hash;
my $enabled_str = $cfg->{'enabled_stacks'} // "ALL";
if ($enabled_str eq "ALL") {
    foreach my $s (@$stacks) { $enabled_hash{$s->{'name'}} = 1; }
} else {
    foreach my $item (split(/,/, $enabled_str)) {
        $item =~ s/^\s+|\s+$//g;
        $enabled_hash{$item} = 1 if ($item ne "");
    }
}

# --- Top Banner & Status Controls ---
print &ui_table_start("Hệ thống Sao lưu Homelab 3-2-1-1-0", "width=100%", 2);

my $status_badge = "";
if ($running) {
    $status_badge = "<span style='color: #1976d2; font-weight: bold; font-size: 15px; background: #e3f2fd; padding: 4px 10px; border-radius: 4px;'>🔄 Đang chạy Backup...</span>";
} elsif ($summary->{'status'} eq 'SUCCESS') {
    $status_badge = "<span style='color: #2e7d32; font-weight: bold; font-size: 15px; background: #e8f5e9; padding: 4px 10px; border-radius: 4px;'>✅ Thành công (Success)</span>";
} elsif ($summary->{'status'} eq 'FAILED') {
    $status_badge = "<span style='color: #c62828; font-weight: bold; font-size: 15px; background: #ffebee; padding: 4px 10px; border-radius: 4px;'>❌ Có lỗi (Failed)</span>";
} else {
    $status_badge = "<span style='color: #616161; font-weight: bold; font-size: 15px; background: #f5f5f5; padding: 4px 10px; border-radius: 4px;'>⚪ Chưa chạy lần nào</span>";
}

my $run_btn = $running 
    ? "<button class='ui_button' disabled style='margin-left: 15px; opacity:0.6;'>Processing...</button>" 
    : "<a href='run.cgi' class='ui_button' style='margin-left: 15px; background-color: #2e7d32; color: white; font-weight: bold;'>🚀 Chạy Backup Tất cả Stack được chọn</a>";

my $log_btn = "<a href='log.cgi' class='ui_button' style='margin-left: 10px;'>📄 Xem Log Chi tiết</a>";
my $config_btn = "<a href='edit_config.cgi?module=$module_name' class='ui_button' style='margin-left: 10px;'>⚙️ Cấu hình Module</a>";

print &ui_table_row("Trạng thái hiện tại", $status_badge . $run_btn . $log_btn . $config_btn);
print &ui_table_row("Lần chạy cuối", "<b>" . &html_escape($summary->{'last_run'}) . "</b>");
print &ui_table_end();

print "<br />";

# --- Section 1: Docker Compose Stacks Selection ---
print &ui_form_start("save_stacks.cgi", "post");
print &ui_table_start("Danh sách Docker Compose Stacks (Quét tại " . &html_escape($cfg->{'local_src'}) . ")", "width=100%", 1);

if (@$stacks) {
    my @table_data;
    foreach my $st (@$stacks) {
        my $sname = &html_escape($st->{'name'});
        my $sdir = &html_escape($st->{'dir'});
        my $checked = $enabled_hash{$st->{'name'}} ? 1 : 0;
        
        my $chk_box = &ui_checkbox("stacks", $st->{'name'}, "", $checked);
        my $status_str = ($st->{'status'} eq 'running')
            ? "<span style='color: green; font-weight: bold;'>● Running (" . $st->{'containers'} . " containers)</span>"
            : "<span style='color: gray;'>○ Stopped</span>";

        my $single_btn = "<a href='run.cgi?stack=" . $st->{'name'} . "' class='ui_button' style='font-size:12px;'>⚡ Backup Stack này</a>";

        push(@table_data, [ $chk_box, "<b>$sname</b>", "<code>$sdir</code>", $status_str, $single_btn ]);
    }
    
    print &ui_columns_table([ "Chọn", "Tên Stack", "Đường dẫn thư mục", "Trạng thái Container", "Thao tác Nhanh" ], 100, \@table_data);
    print "<p style='margin-top: 10px;'>" . &ui_submit("Lưu Lựa chọn Stack Auto-Backup", "save") . "</p>";
} else {
    print "<div style='padding: 15px; text-align: center;'><i>Không tìm thấy file docker-compose.yml nào trong thư mục <code>" . &html_escape($cfg->{'local_src'}) . "</code></i></div>";
}
print &ui_table_end();
print &ui_form_end();

print "<br />";

# --- Section 2: Remote Backup & Cloud Overview ---
print &ui_table_start("Tổng quan Remote Backup & Cloud", "width=100%", 2);
my $remote_status_txt = ($cfg->{'enable_remote'} eq '1')
    ? "<span style='color: green; font-weight: bold;'>BẬT (Enabled)</span>"
    : "<span style='color: gray;'>TẮT (Disabled)</span>";
print &ui_table_row("Trạng thái Remote Backup", $remote_status_txt);

if ($cfg->{'enable_remote'} eq '1') {
    print &ui_table_row("Remote Server IP", "<code>" . &html_escape($cfg->{'remote_user'}) . "@" . &html_escape($cfg->{'remote_ip'}) . ":" . &html_escape($cfg->{'remote_port'}) . "</code>");
    print &ui_table_row("Thư mục Nguồn Remote", "<code>" . &html_escape($cfg->{'remote_src'}) . "</code>");
}

print &ui_table_row("MinIO Remote (Immutable)", "<code>" . &html_escape($cfg->{'minio_remote'}) . "</code>");
print &ui_table_row("Google Drive Remote (Offsite)", "<code>" . &html_escape($cfg->{'cloud_remote'}) . "</code>");
print &ui_table_row("Retention Policy", &html_escape($cfg->{'retention_days'}) . " ngày trên Cloud");
print &ui_table_end();

print "<br />";

# --- Section 3: Quick Cron Settings ---
print &ui_form_start("save_cron.cgi", "post");
print &ui_table_start("Cấu hình Lịch trình Tự động (Cronjob)", "width=100%", 2);
print &ui_table_row("Tự động chạy theo lịch", 
    &ui_yesno_radio("cron_enable", $cfg->{'cron_enable'} // "0"));
print &ui_table_row("Lịch Cron (Phút Giờ Ngày Tháng Thứ)", 
    &ui_textbox("cron_schedule", $cfg->{'cron_schedule'} // "0 2 * * *", 20) . 
    " &nbsp;<span style='color:#666; font-size:12px;'>(Ví dụ: <code>0 2 * * *</code> chạy lúc 02:00 sáng mỗi ngày)</span>");
print &ui_table_row("", &ui_submit("Lưu Lịch trình Cron"));
print &ui_table_end();
print &ui_form_end();

print "<br />";

# --- Section 4: Log Preview ---
my $recent_log = &get_logs(25);
print &ui_table_start("Nhật ký gần đây (/opt/backup_homelab.log)", "width=100%", 1);
print "<p style='margin-bottom: 8px;'><a href='log.cgi' class='ui_button'>Xem toàn bộ Log</a> &nbsp; <a href='index.cgi' class='ui_button'>🔄 Tải lại Trang</a></p>";
print &ui_textarea("logs", $recent_log, 12, 100, "readonly", undef, "style='width:100%; font-family:monospace; background:#1e1e1e; color:#4af626; padding: 10px;'");
print &ui_table_end();

&ui_print_footer("/", $text{'index'});
