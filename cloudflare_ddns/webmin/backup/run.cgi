#!/usr/bin/perl
# run.cgi - Execute Backup (All or Specific Stack) and Stream Output Live

require './homelab-backup-lib.pl';

&ReadParse();
my $target_stack = $in{'stack'} // "";

$| = 1; # Enable autoflush for live streaming

&ui_print_header(undef, "Đang thực thi Homelab Backup", "", undef, 0, 1);

if ($target_stack ne "") {
    print "<h3>⚡ Đang kích hoạt sao lưu riêng cho Stack: <span style='color:#1565c0;'>" . &html_escape($target_stack) . "</span></h3>";
} else {
    print "<h3>🚀 Đang kích hoạt tiến trình sao lưu Homelab 3-2-1-1-0...</h3>";
}

if (&is_backup_running()) {
    print "<div style='color: orange; font-weight: bold; padding: 10px; background: #fff3e0; border: 1px solid #ffe0b2;'>";
    print "⚠️ Tiến trình sao lưu đang được thực thi ngầm! Vui lòng chờ hoặc xem file log.";
    print "</div>";
} else {
    print "<p>Tiến trình đang chạy. Vui lòng không đóng trang này cho tới khi hoàn tất...</p>";
    print "<pre style='background: #1e1e1e; color: #4af626; padding: 15px; border-radius: 5px; max-height: 500px; overflow-y: auto; font-family: monospace;'>";

    my $cmd = "$system_script";
    if ($target_stack ne "") {
        $cmd .= " " . &quote_escape($target_stack);
    }

    open(my $pipe, "$cmd 2>&1 |");
    while (my $line = <$pipe>) {
        print &html_escape($line);
    }
    close($pipe);

    print "</pre>";
    print "<div style='color: green; font-weight: bold; font-size: 15px; margin-top: 10px;'>✅ Đã hoàn tất quá trình sao lưu!</div>";
}

print "<br /><p><a href='index.cgi' class='ui_button'>← Quay lại Dashboard</a> &nbsp; <a href='log.cgi' class='ui_button'>📄 Xem Chi tiết Log</a></p>";

&ui_print_footer("index.cgi", "Dashboard");
