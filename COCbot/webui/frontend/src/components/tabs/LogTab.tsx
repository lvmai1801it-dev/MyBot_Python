import { useState } from "react";
import { Trash2, FolderOpen, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";

export interface LogEntry {
  time: string;
  text: string;
  type: string;
}

interface LogTabProps {
  botLogs: LogEntry[];
  onClearLogs: () => void;
}

export function LogTab({ botLogs, onClearLogs }: LogTabProps) {
  const [logStyle, setLogStyle] = useState("divider");

  const attackLogs = [
    { ac: "1", time: "17:20", base: "DB", search: "14", gold: "650k", elixir: "710k", de: "4.8k", tr: "+18", stars: "2", per: "68%", bGE: "120k", bDE: "800" },
  ];

  return (
    <div className="flex-1 flex flex-col gap-1.5 overflow-hidden h-full">
      {/* KHUNG 1: BOT LOG */}
      <div className="flex-1 bg-slate-900/90 border border-slate-800 rounded-md overflow-hidden flex flex-col">
        <ScrollArea className="flex-1 p-2 font-mono text-[11px]">
          {botLogs.map((log, idx) => (
            <div key={idx} className="leading-[1.45] whitespace-nowrap">
              <span className="text-slate-500 mr-1.5">[{log.time}]</span>
              <span
                className={
                  log.type === "header"
                    ? "text-slate-400 font-bold"
                    : log.type === "warning"
                    ? "text-amber-400"
                    : log.type === "success"
                    ? "text-emerald-400"
                    : "text-slate-200"
                }
              >
                {log.text}
              </span>
            </div>
          ))}
        </ScrollArea>
      </div>

      {/* KHUNG 2: ATTACK LOG */}
      {logStyle !== "bot_only" && (
        <div className="h-32 bg-slate-900/90 border border-slate-800 rounded-md overflow-hidden flex flex-col">
          <div className="bg-slate-950 px-2 py-1 border-b border-slate-800 text-[10px] font-mono text-slate-400 text-center font-semibold">
            ==================== ATTACK LOG ====================
          </div>
          <div className="grid grid-cols-12 bg-slate-950/60 px-1.5 py-1 border-b border-slate-800 font-mono text-[10px] text-slate-400 text-center">
            <span>AC</span>
            <span>TIME</span>
            <span>BASE</span>
            <span>SRCH</span>
            <span className="text-amber-400">GOLD</span>
            <span className="text-pink-400">ELIX</span>
            <span className="text-purple-400">DE</span>
            <span>TR</span>
            <span>*</span>
            <span>%</span>
            <span className="text-emerald-400">B.GE</span>
            <span className="text-emerald-400">B.DE</span>
          </div>
          <ScrollArea className="flex-1 px-1.5 py-1 font-mono text-[10px]">
            {attackLogs.map((row) => (
              <div
                key={row.ac}
                className="grid grid-cols-12 text-center py-0.5 border-b border-slate-800/40 hover:bg-slate-800/40"
              >
                <span className="text-slate-300">{row.ac}</span>
                <span className="text-slate-400">{row.time}</span>
                <span className="text-sky-400">{row.base}</span>
                <span className="text-slate-300">{row.search}</span>
                <span className="text-amber-300">{row.gold}</span>
                <span className="text-pink-300">{row.elixir}</span>
                <span className="text-purple-300">{row.de}</span>
                <span className="text-emerald-400">{row.tr}</span>
                <span className="text-amber-400">{row.stars}</span>
                <span className="text-slate-300">{row.per}</span>
                <span className="text-slate-400">{row.bGE}</span>
                <span className="text-slate-400">{row.bDE}</span>
              </div>
            ))}
          </ScrollArea>
        </div>
      )}

      {/* THANH CÃ”NG Cá»¤ LOG STYLE & 3 NÃšT TRÃ’N */}
      <div className="flex items-center justify-between py-0.5">
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-slate-300 font-medium">Log Style:</span>
          <Select value={logStyle} onValueChange={(value) => setLogStyle(value ?? "")}>
            <SelectTrigger className="h-6 text-[11px] w-[215px] bg-slate-900 border-slate-700 px-2">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs">
              <SelectItem value="divider">Use Divider to Resize Both Logs</SelectItem>
              <SelectItem value="bot_only">Show Bot Log Only</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            variant="outline"
            size="icon"
            className="h-6 w-6 rounded-full border-emerald-500/40 bg-emerald-500/15 hover:bg-emerald-500/30 text-emerald-400"
            title="Copy Log"
          >
            <FileText className="w-3 h-3" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={onClearLogs}
            className="h-6 w-6 rounded-full border-rose-500/40 bg-rose-500/15 hover:bg-rose-500/30 text-rose-400"
            title="Clear Log"
          >
            <Trash2 className="w-3 h-3" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-6 w-6 rounded-full border-amber-500/40 bg-amber-500/15 hover:bg-amber-500/30 text-amber-400"
            title="Open Log Folder"
          >
            <FolderOpen className="w-3 h-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}