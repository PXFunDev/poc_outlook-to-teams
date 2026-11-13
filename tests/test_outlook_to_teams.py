"""Outlookを操作せず、転送対象の判定とCOM呼び出しを検証する。"""

import contextlib
import io
import unittest
from unittest.mock import Mock, patch

import outlook_to_teams as app

TARGET = "channel@example.com"


class ForwardingTests(unittest.TestCase):
    """メール転送とフォルダー操作を検証する。"""

    def test_existing_and_non_mail_items_are_skipped(self):
        """起動時のメールとメール以外を除外し、新規メールだけを転送する。"""
        existing = Mock(Class=app.MAIL_ITEM, EntryID="existing")
        other = Mock(Class=26, EntryID="appointment")
        new = Mock(Class=app.MAIL_ITEM, EntryID="new")
        folder = Mock(Items=[existing, other, new])
        excluded = {"existing"}

        self.assertEqual(app.forward_new_messages(folder, excluded, TARGET), 1)

        existing.Forward.assert_not_called()
        other.Forward.assert_not_called()
        forwarded = new.Forward.return_value
        self.assertEqual(forwarded.To, TARGET)
        self.assertEqual(forwarded.CC, "")
        self.assertEqual(forwarded.BCC, "")
        forwarded.Send.assert_called_once_with()
        new.Move.assert_not_called()
        self.assertEqual(folder.Items, [existing, other, new])
        self.assertEqual(excluded, {"existing", "new"})

        self.assertEqual(app.forward_new_messages(folder, excluded, TARGET), 0)
        forwarded.Send.assert_called_once_with()

    def test_multiple_messages_remain_in_folder(self):
        """複数メールを転送し、元メールとフォルダーを変更しない。"""
        items = [Mock(Class=app.MAIL_ITEM, EntryID=str(i)) for i in range(3)]
        originals = items.copy()
        folder = Mock(Items=items)
        excluded = set()

        self.assertEqual(app.forward_new_messages(folder, excluded, TARGET), 3)
        self.assertEqual(items, originals)
        self.assertEqual(app.forward_new_messages(folder, excluded, TARGET), 0)
        folder.Folders.Add.assert_not_called()
        for item in originals:
            item.Forward.return_value.Send.assert_called_once_with()
            item.Move.assert_not_called()
            item.Delete.assert_not_called()

    def test_send_error_propagates_without_moving(self):
        """送信失敗は伝播し、元メールの移動と除外登録を行わない。"""
        item = Mock(Class=app.MAIL_ITEM, EntryID="new")
        item.Forward.return_value.Send.side_effect = RuntimeError("送信失敗")
        excluded = set()

        with self.assertRaisesRegex(RuntimeError, "送信失敗"):
            app.forward_new_messages(Mock(Items=[item]), excluded, TARGET)

        item.Move.assert_not_called()
        self.assertEqual(excluded, set())

    def test_resolve_folder_hierarchy(self):
        """メールボックス名と階層ごとの名前でフォルダーを解決する。"""
        namespace = Mock()
        mailbox = namespace.Folders.Item.return_value
        inbox = mailbox.Folders.Item.return_value

        result = app.get_folder(namespace, "Mailbox", ["受信トレイ", "Teams転送"])

        namespace.Folders.Item.assert_called_once_with("Mailbox")
        mailbox.Folders.Item.assert_called_once_with("受信トレイ")
        inbox.Folders.Item.assert_called_once_with("Teams転送")
        self.assertIs(result, inbox.Folders.Item.return_value)

    def test_missing_folder_error_propagates(self):
        """指定フォルダーが存在しない場合にエラーを伝播する。"""
        namespace = Mock()
        namespace.Folders.Item.side_effect = RuntimeError("見つかりません")

        with self.assertRaisesRegex(RuntimeError, "見つかりません"):
            app.get_folder(namespace, "Mailbox", ["Teams転送"])

    def test_monitor_excludes_startup_and_downtime_mail(self):
        """監視ループと再起動で既存メールを除外し、稼働中の追加分だけ転送する。"""
        win32com = Mock()
        namespace = win32com.client.Dispatch.return_value.GetNamespace.return_value
        folder = namespace.Folders.Item.return_value.Folders.Item.return_value
        existing = Mock(Class=app.MAIL_ITEM, EntryID="existing")
        new = Mock(Class=app.MAIL_ITEM, EntryID="new")
        folder.Items = [existing]
        argv = [
            "--mailbox",
            "Mailbox",
            "--folder",
            "Teams転送",
            "--teams-email",
            TARGET,
        ]

        def wait_or_stop(_):
            """最初の待機でメールを追加し、次の待機で監視を終了する。"""
            if new.Forward.called:
                raise KeyboardInterrupt
            folder.Items.append(new)

        with (
            patch.dict(
                "sys.modules",
                {"win32com": win32com, "win32com.client": win32com.client},
            ),
            patch.object(app.time, "sleep", side_effect=wait_or_stop) as sleep,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            app.main(argv)
            sleep.assert_called_with(10)
            downtime = Mock(Class=app.MAIL_ITEM, EntryID="downtime")
            folder.Items.append(downtime)
            sleep.side_effect = KeyboardInterrupt
            app.main(argv)

        existing.Forward.assert_not_called()
        downtime.Forward.assert_not_called()
        new.Forward.return_value.Send.assert_called_once_with()
        new.Move.assert_not_called()
        folder.Folders.Add.assert_not_called()
        self.assertEqual(folder.Items, [existing, new, downtime])


class ConfigurationTests(unittest.TestCase):
    """コマンドライン引数の検証を行う。"""

    def test_constants_are_used_without_arguments(self):
        """引数を省略すると定数の設定を利用する。"""
        with (
            patch.object(app, "OUTLOOK_MAILBOX", "定数のメールボックス"),
            patch.object(app, "OUTLOOK_FOLDER", ("受信トレイ", "定数のフォルダー")),
            patch.object(app, "TEAMS_CHANNEL_EMAIL", TARGET),
        ):
            args = app.parse_args([])
        self.assertEqual(args.mailbox, "定数のメールボックス")
        self.assertEqual(args.folder, ["受信トレイ", "定数のフォルダー"])
        self.assertEqual(args.teams_email, TARGET)

    def test_invalid_constant_configuration(self):
        """定数の未設定と不正値も起動時に拒否する。"""
        invalid = [
            ("", ("Inbox",), TARGET),
            ("Mailbox", (), TARGET),
            ("Mailbox", (" ",), TARGET),
            ("Mailbox", ("Inbox",), ""),
            ("Mailbox", ("Inbox",), "invalid"),
        ]
        for mailbox, folder, email in invalid:
            with (
                self.subTest(mailbox=mailbox, folder=folder, email=email),
                patch.object(app, "OUTLOOK_MAILBOX", mailbox),
                patch.object(app, "OUTLOOK_FOLDER", folder),
                patch.object(app, "TEAMS_CHANNEL_EMAIL", email),
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as raised,
            ):
                app.parse_args([])
            self.assertEqual(raised.exception.code, 2)

    def test_valid_configuration(self):
        """階層を含む有効な設定を受け取る。"""
        args = app.parse_args(
            [
                "--mailbox",
                "Mailbox",
                "--folder",
                "受信トレイ",
                "Teams転送",
                "--teams-email",
                TARGET,
            ]
        )
        self.assertEqual(args.mailbox, "Mailbox")
        self.assertEqual(args.folder, ["受信トレイ", "Teams転送"])
        self.assertEqual(args.teams_email, TARGET)

    def test_invalid_configuration(self):
        """未設定・空白・複数宛先・不正アドレスで起動を拒否する。"""
        invalid = [
            [],
            ["--mailbox", " ", "--folder", "Inbox", "--teams-email", TARGET],
            ["--mailbox", "Mailbox", "--folder", " ", "--teams-email", TARGET],
        ]
        for address in ("invalid", "a@b;c@d", "a@b,c@d", "a@b\nBcc:c@d"):
            invalid.append(
                ["--mailbox", "Mailbox", "--folder", "Inbox", "--teams-email", address]
            )
        for argv in invalid:
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    app.parse_args(argv)
                self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
