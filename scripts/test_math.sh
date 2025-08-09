PROMPT="ある村にはリンゴ農家が4軒あります。
1軒目は120個、2軒目は150個のリンゴを収穫しました。
3軒目は1軒目と2軒目の合計の半分を収穫し、4軒目は3軒目より60個多く収穫しました。
村祭りの日、次のことが起こりました：

村全体のリンゴの総収穫数から、5分の1を来場者に配りました。
残りのリンゴを4軒の農家で均等に分けました。
均等分配されたあとの各農家の手持ちから、2箱分（1箱12個）を市場に出しました。
このとき、市場に出した後に農家の手元に残っているリンゴの合計は何個になりますか？"

uv run python -m cli --model gpt-5 cfg-math \
   --prompt "$PROMPT" --expect 384
uv run python -m cli --model gpt-5-mini cfg-math \
   --prompt "$PROMPT" --expect 384
uv run python -m cli --model gpt-5-nano cfg-math \
   --prompt "$PROMPT" --expect 384
