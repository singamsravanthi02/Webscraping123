"use client";

import { useCallback, useEffect, useState } from "react";
import { Bell, CheckCheck, Loader2, Mail, Smartphone, Trash2, RefreshCcw, Clock3, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";
import { toast } from "sonner";

type NotificationItem = {
  id: number;
  template_name: string;
  channel: string;
  status: string;
  is_read: boolean;
  error_message?: string | null;
  created_at: string;
  sent_at?: string | null;
  context_data?: {
    subject?: string;
    message?: string;
  } | null;
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await api.get("/notifications/me?limit=100");
      setNotifications(res.data || []);
    } catch (error) {
      console.error(error);
      setNotifications([]);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchNotifications();
    }, 0);
    const interval = window.setInterval(() => {
      void fetchNotifications();
    }, 15000);
    return () => {
      window.clearTimeout(timer);
      window.clearInterval(interval);
    };
  }, [fetchNotifications]);

  const unreadCount = notifications.filter((notification) => !notification.is_read).length;

  const markRead = async (id: number) => {
    try {
      await api.post(`/notifications/me/${id}/read`);
      setNotifications((current) => current.map((item) => (item.id === id ? { ...item, is_read: true } : item)));
    } catch (error) {
      console.error(error);
      toast.error("Failed to mark notification as read");
    }
  };

  const markAllRead = async () => {
    try {
      await api.post("/notifications/me/read-all");
      setNotifications((current) => current.map((item) => ({ ...item, is_read: true })));
      toast.success("All notifications marked as read");
    } catch (error) {
      console.error(error);
      toast.error("Failed to mark all notifications as read");
    }
  };

  const deleteNotification = async (id: number) => {
    try {
      await api.delete(`/notifications/me/${id}`);
      setNotifications((current) => current.filter((item) => item.id !== id));
      toast.success("Notification deleted");
    } catch (error) {
      console.error(error);
      toast.error("Failed to delete notification");
    }
  };

  const refresh = async () => {
    setIsRefreshing(true);
    await fetchNotifications();
  };

  const getChannelIcon = (channel: string) => {
    switch (channel.toLowerCase()) {
      case "email":
        return <Mail className="h-4 w-4" />;
      case "sms":
        return <Smartphone className="h-4 w-4" />;
      default:
        return <Bell className="h-4 w-4" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case "sent":
        return <CheckCheck className="h-4 w-4 text-emerald-400" />;
      case "failed":
        return <AlertCircle className="h-4 w-4 text-red-400" />;
      default:
        return <Clock3 className="h-4 w-4 text-yellow-400" />;
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex flex-col gap-4 rounded-3xl border border-border bg-background p-6 shadow-sm md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm uppercase tracking-wide text-muted-foreground">
            <Bell className="h-4 w-4" />
            Notifications
          </div>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">Your Inbox</h1>
          <p className="text-muted-foreground">Read, delete, and keep track of system alerts.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void refresh()} disabled={isRefreshing}>
            {isRefreshing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCcw className="mr-2 h-4 w-4" />}
            Refresh
          </Button>
          <Button onClick={() => void markAllRead()} disabled={unreadCount === 0}>
            <CheckCheck className="mr-2 h-4 w-4" />
            Mark all read
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Total</CardDescription>
            <CardTitle>{notifications.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Unread</CardDescription>
            <CardTitle>{unreadCount}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Read</CardDescription>
            <CardTitle>{notifications.length - unreadCount}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="space-y-4">
        {isLoading ? (
          <div className="flex min-h-64 items-center justify-center rounded-2xl border border-dashed border-border">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : notifications.length === 0 ? (
          <Card>
            <CardContent className="py-16 text-center text-muted-foreground">
              No notifications yet.
            </CardContent>
          </Card>
        ) : (
          notifications.map((notification) => (
            <Card key={notification.id} className={!notification.is_read ? "border-primary/30" : ""}>
              <CardContent className="p-5">
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={notification.is_read ? "outline" : "default"}>{notification.is_read ? "Read" : "Unread"}</Badge>
                      <span className="flex items-center gap-1 text-xs uppercase tracking-wide text-muted-foreground">
                        {getChannelIcon(notification.channel)}
                        {notification.channel}
                      </span>
                      <span className="flex items-center gap-1 text-xs uppercase tracking-wide text-muted-foreground">
                        {getStatusIcon(notification.status)}
                        {notification.status}
                      </span>
                    </div>
                    <div>
                      <h3 className="font-semibold">{notification.context_data?.subject || notification.template_name}</h3>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {notification.context_data?.message || notification.error_message || "No message available."}
                      </p>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {new Date(notification.created_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="flex gap-2">
                    {!notification.is_read && (
                      <Button variant="outline" size="sm" onClick={() => void markRead(notification.id)}>
                        <CheckCheck className="mr-2 h-4 w-4" />
                        Read
                      </Button>
                    )}
                    <Button variant="destructive" size="sm" onClick={() => void deleteNotification(notification.id)}>
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
