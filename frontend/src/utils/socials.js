import {
  Instagram, Facebook, MessageCircle, Twitter, Music2,
  Youtube, Linkedin, Send, Twitch, Globe
} from 'lucide-vue-next'

/**
 * Redes sociales soportadas (deben coincidir con SOCIAL_NETWORKS del backend).
 * Cada una tiene su icono; "website" sirve de comodín para cualquier otro enlace.
 */
export const SOCIAL_NETWORKS = [
  { key: 'instagram', label: 'Instagram', icon: Instagram },
  { key: 'facebook', label: 'Facebook', icon: Facebook },
  { key: 'whatsapp', label: 'WhatsApp', icon: MessageCircle },
  { key: 'x', label: 'X (Twitter)', icon: Twitter },
  { key: 'tiktok', label: 'TikTok', icon: Music2 },
  { key: 'youtube', label: 'YouTube', icon: Youtube },
  { key: 'linkedin', label: 'LinkedIn', icon: Linkedin },
  { key: 'telegram', label: 'Telegram', icon: Send },
  { key: 'twitch', label: 'Twitch', icon: Twitch },
  { key: 'website', label: 'Sitio web / Otro', icon: Globe }
]

const byKey = (key) => SOCIAL_NETWORKS.find((n) => n.key === key)

export const socialIcon = (key) => byKey(key)?.icon || Globe
export const socialLabel = (key) => byKey(key)?.label || key
