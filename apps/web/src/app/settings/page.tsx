"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  createAccount,
  deleteAccount,
  getSupportedExchanges,
  listAccounts,
  updateAccount,
  type CreateExchangeAccountRequest,
  type ExchangeAccountResponse,
} from "@/lib/exchange-accounts";

const inputClasses =
  "w-full bg-transparent border border-border rounded-md px-3 py-1.5 text-sm font-mono placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-ring";

const selectClasses =
  "w-full bg-transparent border border-border rounded-md px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-ring";

interface DialogForm {
  label: string;
  exchange_id: string;
  api_key: string;
  api_secret: string;
  passphrase: string;
  mode: "sandbox" | "live";
  is_default: boolean;
}

const emptyForm: DialogForm = {
  label: "",
  exchange_id: "",
  api_key: "",
  api_secret: "",
  passphrase: "",
  mode: "sandbox",
  is_default: false,
};

export default function SettingsPage() {
  const [accounts, setAccounts] = useState<ExchangeAccountResponse[]>([]);
  const [exchanges, setExchanges] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<DialogForm>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listAccounts(), getSupportedExchanges()])
      .then(([accts, exs]) => {
        setAccounts(accts);
        setExchanges(exs);
      })
      .finally(() => setLoading(false));
  }, []);

  function openAdd() {
    setEditingId(null);
    setForm(emptyForm);
    setError(null);
    setDialogOpen(true);
  }

  function openEdit(account: ExchangeAccountResponse) {
    setEditingId(account.id);
    setForm({
      label: account.label,
      exchange_id: account.exchange_id,
      api_key: "",
      api_secret: "",
      passphrase: "",
      mode: account.mode as "sandbox" | "live",
      is_default: account.is_default,
    });
    setError(null);
    setDialogOpen(true);
  }

  function closeDialog() {
    setDialogOpen(false);
    setEditingId(null);
    setForm(emptyForm);
    setError(null);
  }

  async function handleSave() {
    if (!form.label.trim() || !form.exchange_id) {
      setError("标签和交易所不能为空");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (editingId) {
        const updated = await updateAccount(editingId, {
          label: form.label,
          ...(form.api_key ? { api_key: form.api_key } : {}),
          ...(form.api_secret ? { api_secret: form.api_secret } : {}),
          ...(form.passphrase ? { passphrase: form.passphrase } : {}),
          mode: form.mode,
          is_default: form.is_default,
        });
        setAccounts((prev) =>
          prev.map((a) => (a.id === editingId ? updated : a))
        );
        if (form.is_default) {
          setAccounts((prev) =>
            prev.map((a) =>
              a.id !== editingId ? { ...a, is_default: false } : a
            )
          );
        }
      } else {
        if (!form.api_key || !form.api_secret) {
          setError("API Key 和 Secret 不能为空");
          setSaving(false);
          return;
        }
        const req: CreateExchangeAccountRequest = {
          label: form.label,
          exchange_id: form.exchange_id,
          api_key: form.api_key,
          api_secret: form.api_secret,
          mode: form.mode,
          is_default: form.is_default,
        };
        if (form.passphrase) req.passphrase = form.passphrase;
        const created = await createAccount(req);
        setAccounts((prev) => {
          const withoutDefault = form.is_default
            ? prev.map((a) => ({ ...a, is_default: false }))
            : prev;
          return [...withoutDefault, created];
        });
      }
      closeDialog();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteAccount(id);
      setAccounts((prev) => prev.filter((a) => a.id !== id));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "删除失败");
    } finally {
      setConfirmDeleteId(null);
    }
  }

  async function handleSetDefault(account: ExchangeAccountResponse) {
    try {
      const updated = await updateAccount(account.id, { is_default: true });
      setAccounts((prev) =>
        prev.map((a) =>
          a.id === account.id ? updated : { ...a, is_default: false }
        )
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "操作失败");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-light tracking-wide">系统设置</h1>
        <p className="mt-1 text-xs font-light text-muted-foreground">
          Settings — Exchange accounts, risk parameters
        </p>
      </div>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs font-light tracking-wide">交易所账户</span>
            <span className="ml-2 text-[10px] font-light text-muted-foreground">
              Exchange Accounts
            </span>
          </div>
          <Button variant="outline" size="sm" onClick={openAdd}>
            添加账户
          </Button>
        </div>

        {loading ? (
          <div className="rounded-md border border-border/50 bg-card p-6">
            <p className="text-xs font-light text-muted-foreground/50">
              加载中…
            </p>
          </div>
        ) : accounts.length === 0 ? (
          <div className="rounded-md border border-border/50 bg-card p-6">
            <p className="text-xs font-light text-muted-foreground/50">
              暂无账户，点击「添加账户」开始
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {accounts.map((account) => (
              <div
                key={account.id}
                className={cn(
                  "rounded-md border bg-card p-4",
                  account.mode === "live"
                    ? "border-destructive/50"
                    : "border-border/50"
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-light tracking-wide truncate">
                        {account.label}
                      </span>
                      {account.is_default && (
                        <span className="text-[10px] tracking-widest uppercase border border-border/50 rounded px-1.5 py-0.5">
                          默认
                        </span>
                      )}
                      <span
                        className={cn(
                          "text-[10px] tracking-widest uppercase rounded px-1.5 py-0.5",
                          account.mode === "live"
                            ? "border border-destructive/50 text-destructive"
                            : "border border-border/50 text-muted-foreground"
                        )}
                      >
                        {account.mode}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                      <span className="uppercase tracking-widest">
                        {account.exchange_id}
                      </span>
                      <span className="font-mono">{account.api_key_hint}</span>
                      {account.has_passphrase && (
                        <span className="tracking-widest">+ passphrase</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {!account.is_default && (
                      <button
                        onClick={() => handleSetDefault(account)}
                        className="text-[10px] tracking-widest uppercase text-muted-foreground hover:text-foreground transition-colors"
                      >
                        设为默认
                      </button>
                    )}
                    <button
                      onClick={() => openEdit(account)}
                      className="text-[10px] tracking-widest uppercase text-muted-foreground hover:text-foreground transition-colors"
                    >
                      编辑
                    </button>
                    {confirmDeleteId === account.id ? (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleDelete(account.id)}
                          className="text-[10px] tracking-widest uppercase text-destructive hover:text-destructive/80 transition-colors"
                        >
                          确认
                        </button>
                        <button
                          onClick={() => setConfirmDeleteId(null)}
                          className="text-[10px] tracking-widest uppercase text-muted-foreground hover:text-foreground transition-colors"
                        >
                          取消
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmDeleteId(account.id)}
                        className="text-[10px] tracking-widest uppercase text-muted-foreground hover:text-destructive transition-colors"
                      >
                        删除
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {dialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-md rounded-md border border-border bg-background p-6 shadow-lg space-y-4">
            <div>
              <span className="text-sm font-light tracking-wide">
                {editingId ? "编辑账户" : "添加账户"}
              </span>
              <p className="text-[10px] font-light text-muted-foreground mt-0.5">
                {editingId ? "Edit Exchange Account" : "Add Exchange Account"}
              </p>
            </div>

            <div className="space-y-3">
              <div className="space-y-1.5">
                <label className="block text-xs font-light tracking-wide">
                  标签 <span className="ml-1 text-[10px] text-muted-foreground">Label</span>
                </label>
                <input
                  type="text"
                  value={form.label}
                  onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
                  placeholder="My Binance Sandbox"
                  className={inputClasses}
                />
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-light tracking-wide">
                  交易所 <span className="ml-1 text-[10px] text-muted-foreground">Exchange</span>
                </label>
                <select
                  value={form.exchange_id}
                  onChange={(e) => setForm((f) => ({ ...f, exchange_id: e.target.value }))}
                  className={selectClasses}
                >
                  <option value="">选择交易所…</option>
                  {exchanges.map((ex) => (
                    <option key={ex} value={ex}>
                      {ex}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-light tracking-wide">
                  API Key{editingId && (
                    <span className="ml-1 text-[10px] text-muted-foreground">留空则不更新</span>
                  )}
                </label>
                <input
                  type="password"
                  value={form.api_key}
                  onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
                  placeholder={editingId ? "（留空不修改）" : "API Key"}
                  className={inputClasses}
                />
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-light tracking-wide">
                  API Secret{editingId && (
                    <span className="ml-1 text-[10px] text-muted-foreground">留空则不更新</span>
                  )}
                </label>
                <input
                  type="password"
                  value={form.api_secret}
                  onChange={(e) => setForm((f) => ({ ...f, api_secret: e.target.value }))}
                  placeholder={editingId ? "（留空不修改）" : "API Secret"}
                  className={inputClasses}
                />
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-light tracking-wide">
                  Passphrase <span className="ml-1 text-[10px] text-muted-foreground">可选 Optional</span>
                </label>
                <input
                  type="password"
                  value={form.passphrase}
                  onChange={(e) => setForm((f) => ({ ...f, passphrase: e.target.value }))}
                  placeholder="（如 OKX 需要）"
                  className={inputClasses}
                />
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-light tracking-wide">
                  模式 <span className="ml-1 text-[10px] text-muted-foreground">Mode</span>
                </label>
                <div className="flex overflow-hidden rounded-md border border-border">
                  {(["sandbox", "live"] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setForm((f) => ({ ...f, mode: m }))}
                      className={cn(
                        "flex-1 py-1.5 text-[10px] tracking-widest uppercase transition-colors",
                        form.mode === m
                          ? m === "live"
                            ? "bg-destructive text-destructive-foreground"
                            : "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {m}
                    </button>
                  ))}
                </div>
                {form.mode === "live" && (
                  <p className="text-[10px] text-destructive">
                    实盘模式将直接操作真实资金，请谨慎操作。
                  </p>
                )}
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_default"
                  checked={form.is_default}
                  onChange={(e) => setForm((f) => ({ ...f, is_default: e.target.checked }))}
                  className="rounded border-border"
                />
                <label htmlFor="is_default" className="text-xs font-light tracking-wide cursor-pointer">
                  设为默认账户
                </label>
              </div>
            </div>

            {error && (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
                {error}
              </div>
            )}

            <div className="flex gap-2 pt-1">
              <Button
                variant="outline"
                className="flex-1"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? "保存中…" : "保存"}
              </Button>
              <Button
                variant="ghost"
                className="flex-1"
                onClick={closeDialog}
                disabled={saving}
              >
                取消
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
