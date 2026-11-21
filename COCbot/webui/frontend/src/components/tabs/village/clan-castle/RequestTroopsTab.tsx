import { useState } from "react";
import { Star, Castle } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";

export function RequestTroopsTab() {
  const [requestEnabled, setRequestEnabled] = useState(false);
  const [requestText, setRequestText] = useState("Anything please");
  const [amHours, setAmHours] = useState<boolean[]>(Array(12).fill(true));
  const [pmHours, setPmHours] = useState<boolean[]>(Array(12).fill(true));

  return (
    <fieldset className="h-full border border-slate-800 bg-slate-900/60 rounded-md px-3 py-2 flex flex-col justify-between text-[10px]">
      <legend className="px-1 text-[10px] font-semibold text-slate-400">
        Clan Castle Troops
      </legend>

      {/* Pháº§n trÃªn: Checkbox & Ã” nháº­p text xin quÃ¢n */}
      <div className="flex items-start gap-3 pt-1">
        <div className="w-14 h-14 rounded-lg bg-sky-500/10 border border-sky-500/30 flex flex-col items-center justify-center shrink-0">
          <Castle className="w-6 h-6 text-sky-400 mb-0.5" />
          <span className="text-[9px] font-bold text-sky-300 uppercase">Request</span>
        </div>

        <div className="flex-1 flex flex-col gap-2">
          <div className="flex items-center gap-1.5">
            <Checkbox
              id="cc-req-enable"
              checked={requestEnabled}
              onCheckedChange={(v) => setRequestEnabled(v as boolean)}
              className="h-3.5 w-3.5 border-slate-600 data-[state=checked]:bg-emerald-600"
            />
            <label htmlFor="cc-req-enable" className="text-slate-200 font-medium cursor-pointer">
              Request Troops / Spells
            </label>
          </div>

          <Input
            disabled={!requestEnabled}
            value={requestText}
            onChange={(e) => setRequestText(e.target.value)}
            placeholder="Enter request message..."
            className="h-7 text-[11px] text-center bg-slate-950 border-slate-700"
          />
        </div>
      </div>

      {/* Pháº§n dÆ°á»›i: LÆ°á»›i chá»n 24 giá» AM / PM */}
      <div className="pb-1">
        <div className="text-slate-300 mb-1.5 font-medium">
          Only during these hours of each day
        </div>

        <div className="bg-slate-950/70 border border-slate-800 rounded p-2">
          <div className="grid grid-cols-14 items-center text-center font-mono text-[9px] text-slate-400 mb-1">
            <span className="col-span-1 text-left">Hour:</span>
            {Array.from({ length: 12 }).map((_, i) => (
              <span key={i}>{i}</span>
            ))}
            <span title="Toggle All">Ã—</span>
          </div>

          {/* HÃ ng AM */}
          <div className="grid grid-cols-14 items-center text-center mb-1.5">
            <span className="col-span-1 text-left font-semibold text-slate-300 text-[9px]">
              AM
            </span>
            {amHours.map((checked, idx) => (
              <div key={idx} className="flex justify-center">
                <Checkbox
                  disabled={!requestEnabled}
                  checked={checked}
                  onCheckedChange={(v) => {
                    const next = [...amHours];
                    next[idx] = v as boolean;
                    setAmHours(next);
                  }}
                  className="h-3 w-3 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
              </div>
            ))}
            <button
              type="button"
              disabled={!requestEnabled}
              onClick={() => setAmHours(Array(12).fill(!amHours.every(Boolean)))}
              className="flex justify-center text-amber-400 hover:text-amber-300 disabled:opacity-40"
              title="Toggle all AM hours"
            >
              <Star className="w-3 h-3 fill-amber-400" />
            </button>
          </div>

          {/* HÃ ng PM */}
          <div className="grid grid-cols-14 items-center text-center">
            <span className="col-span-1 text-left font-semibold text-slate-300 text-[9px]">
              PM
            </span>
            {pmHours.map((checked, idx) => (
              <div key={idx} className="flex justify-center">
                <Checkbox
                  disabled={!requestEnabled}
                  checked={checked}
                  onCheckedChange={(v) => {
                    const next = [...pmHours];
                    next[idx] = v as boolean;
                    setPmHours(next);
                  }}
                  className="h-3 w-3 border-slate-600 data-[state=checked]:bg-emerald-600"
                />
              </div>
            ))}
            <button
              type="button"
              disabled={!requestEnabled}
              onClick={() => setPmHours(Array(12).fill(!pmHours.every(Boolean)))}
              className="flex justify-center text-amber-400 hover:text-amber-300 disabled:opacity-40"
              title="Toggle all PM hours"
            >
              <Star className="w-3 h-3 fill-amber-400" />
            </button>
          </div>
        </div>
      </div>
    </fieldset>
  );
}