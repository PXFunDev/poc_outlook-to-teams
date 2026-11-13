"""クラシックOutlookのフォルダーに追加されたメールをTeamsへ転送する。"""

import argparse
import re
import time

OUTLOOK_MAILBOX = ""
OUTLOOK_FOLDER = ("受信トレイ", "Teams転送")
TEAMS_CHANNEL_EMAIL = ""

MAIL_ITEM = 43
POLL_SECONDS = 10


def nonempty(value: str) -> str:
    """空白のみの引数を拒否し、値を返す。空の場合はArgumentTypeErrorを送出する。"""
    if not value.strip():
        raise argparse.ArgumentTypeError("空白だけの値は指定できません。")
    return value


def channel_email(value: str) -> str:
    """単一のメールアドレスを返す。不正な引数にはArgumentTypeErrorを送出する。"""
    if not re.fullmatch(r"[^@\s;,<>]+@[^@\s;,<>]+", value):
        raise argparse.ArgumentTypeError(
            "Teamsチャネルのメールアドレスを1件だけ指定してください。"
        )
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """定数を既定値として引数列を解析する。未設定や不正値はSystemExitで終了する。"""
    parser = argparse.ArgumentParser(
        description="Outlookの新規メールをTeamsチャネルへ転送します。"
    )
    parser.add_argument(
        "--mailbox",
        default=OUTLOOK_MAILBOX,
        type=nonempty,
        help="Outlook上のメールボックス表示名",
    )
    parser.add_argument(
        "--folder",
        default=list(OUTLOOK_FOLDER),
        nargs="+",
        type=nonempty,
        help="監視フォルダーまでの名前を階層順に空白区切りで指定",
    )
    parser.add_argument(
        "--teams-email",
        default=TEAMS_CHANNEL_EMAIL,
        type=channel_email,
        help="Teamsチャネルのメールアドレス（1件）",
    )
    args = parser.parse_args(argv)
    if not args.folder or any(not name.strip() for name in args.folder):
        parser.error("監視フォルダー名を階層順に1件以上指定してください。")
    return args


def get_folder(namespace, mailbox: str, folder_names: list[str]):
    """名前の階層から監視フォルダーを返す。存在しない場合のCOMエラーは伝播する。"""
    folder = namespace.Folders.Item(mailbox)
    for name in folder_names:
        folder = folder.Folders.Item(name)
    return folder


def forward_new_messages(folder, excluded_ids: set[str], teams_email: str) -> int:
    """未除外メールを転送し件数を返す。除外IDを更新し、COMエラーは伝播する。"""
    count = 0
    for item in list(folder.Items):
        if item.Class != MAIL_ITEM or item.EntryID in excluded_ids:
            continue
        entry_id = item.EntryID
        forwarded = item.Forward()
        forwarded.To = teams_email
        forwarded.CC = ""
        forwarded.BCC = ""
        forwarded.Send()
        excluded_ids.add(entry_id)
        count += 1
    return count


def main(argv: list[str] | None = None) -> None:
    """引数で指定したフォルダーを監視する。設定・COMエラーは伝播し、Ctrl+Cで終了する。"""
    args = parse_args(argv)

    import win32com.client

    outlook = win32com.client.Dispatch("Outlook.Application")
    folder = get_folder(outlook.GetNamespace("MAPI"), args.mailbox, args.folder)
    excluded_ids = {item.EntryID for item in list(folder.Items)}
    print("監視を開始しました。起動時の既存メールは対象外です。Ctrl+Cで終了します。")
    try:
        while True:
            count = forward_new_messages(folder, excluded_ids, args.teams_email)
            if count:
                print(f"{count}件を送信依頼しました。")
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\n監視を終了しました。")


if __name__ == "__main__":
    main()
