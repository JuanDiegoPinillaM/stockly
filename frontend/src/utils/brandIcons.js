import {
  Store, ShoppingBag, ShoppingCart, Package, Gem, Crown, Leaf, Heart,
  Star, Sparkles, Coffee, Shirt, Gift, Flower2, Cake, Utensils,
  Wrench, Book, Bike, PawPrint, Stethoscope, Scissors, Dumbbell, Laptop,
  Truck, Tag, Percent, BadgeCheck, Megaphone, Bell, Clock, MapPin,
  ShieldCheck, Flame, PartyPopper, Zap
} from 'lucide-vue-next'

/**
 * Iconos de marca seleccionables para el logotipo cuando no se sube una imagen.
 * Se guarda solo la clave (string); el front la mapea al componente.
 */
export const BRAND_ICONS = [
  { key: 'Store', icon: Store },
  { key: 'ShoppingBag', icon: ShoppingBag },
  { key: 'ShoppingCart', icon: ShoppingCart },
  { key: 'Package', icon: Package },
  { key: 'Gem', icon: Gem },
  { key: 'Crown', icon: Crown },
  { key: 'Leaf', icon: Leaf },
  { key: 'Heart', icon: Heart },
  { key: 'Star', icon: Star },
  { key: 'Sparkles', icon: Sparkles },
  { key: 'Coffee', icon: Coffee },
  { key: 'Shirt', icon: Shirt },
  { key: 'Gift', icon: Gift },
  { key: 'Flower2', icon: Flower2 },
  { key: 'Cake', icon: Cake },
  { key: 'Utensils', icon: Utensils },
  { key: 'Wrench', icon: Wrench },
  { key: 'Book', icon: Book },
  { key: 'Bike', icon: Bike },
  { key: 'PawPrint', icon: PawPrint },
  { key: 'Stethoscope', icon: Stethoscope },
  { key: 'Scissors', icon: Scissors },
  { key: 'Dumbbell', icon: Dumbbell },
  { key: 'Laptop', icon: Laptop }
]

export const brandIcon = (key) => BRAND_ICONS.find((i) => i.key === key)?.icon || null

/**
 * Iconos seleccionables para la barra de anuncio (franja superior).
 */
export const ANNOUNCE_ICONS = [
  { key: 'Truck', icon: Truck },
  { key: 'Tag', icon: Tag },
  { key: 'Percent', icon: Percent },
  { key: 'Gift', icon: Gift },
  { key: 'Sparkles', icon: Sparkles },
  { key: 'BadgeCheck', icon: BadgeCheck },
  { key: 'Megaphone', icon: Megaphone },
  { key: 'Bell', icon: Bell },
  { key: 'Clock', icon: Clock },
  { key: 'MapPin', icon: MapPin },
  { key: 'ShieldCheck', icon: ShieldCheck },
  { key: 'Flame', icon: Flame },
  { key: 'PartyPopper', icon: PartyPopper },
  { key: 'Zap', icon: Zap },
  { key: 'Star', icon: Star },
  { key: 'Heart', icon: Heart }
]

export const announceIcon = (key) => ANNOUNCE_ICONS.find((i) => i.key === key)?.icon || null
