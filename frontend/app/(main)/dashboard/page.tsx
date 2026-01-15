'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Users, 
  MessageSquare, 
  Video, 
  TrendingUp,
  Bot,
  Bell,
  Settings,
  ChevronRight,
  X,
  Check,
  Trash2,
  Loader2,
  Key,
  Database,
  RefreshCw,
  ExternalLink,
  Building2,
  Package,
  Globe,
  Star,
  DollarSign,
  Save
} from 'lucide-react'
import Link from 'next/link'

// 动画配置
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
}

// 通知弹窗
function NotificationsModal({ 
  isOpen, 
  onClose,
  notifications,
  onMarkRead,
  onClearAll
}: { 
  isOpen: boolean
  onClose: () => void
  notifications: Array<{ id: string; title: string; content: string; time: string; read: boolean }>
  onMarkRead: (id: string) => void
  onClearAll: () => void
}) {
  if (!isOpen) return null
  
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/60"
      onClick={onClose}
    >
      <motion.div 
        initial={{ scale: 0.95, y: -20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: -20 }}
        className="glass-card w-full max-w-md mx-4 max-h-[70vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-cyber-blue" />
            <h2 className="font-bold">通知中心</h2>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={onClearAll}
              className="text-xs text-gray-400 hover:text-cyber-blue transition-colors"
            >
              全部已读
            </button>
            <button 
              onClick={onClose}
              className="p-1 hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        <div className="overflow-y-auto max-h-[50vh]">
          {notifications.length === 0 ? (
            <div className="p-8 text-center">
              <Bell className="w-10 h-10 text-gray-600 mx-auto mb-2" />
              <p className="text-gray-500">暂无通知</p>
            </div>
          ) : (
            notifications.map((notif) => (
              <div 
                key={notif.id}
                onClick={() => onMarkRead(notif.id)}
                className={`p-4 border-b border-white/5 cursor-pointer transition-colors hover:bg-white/5 ${
                  !notif.read ? 'bg-cyber-blue/5' : ''
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-2 h-2 mt-2 rounded-full ${notif.read ? 'bg-gray-600' : 'bg-cyber-blue animate-pulse'}`} />
                  <div className="flex-1">
                    <p className="font-medium text-sm">{notif.title}</p>
                    <p className="text-gray-400 text-xs mt-1">{notif.content}</p>
                    <p className="text-gray-500 text-xs mt-2">{notif.time}</p>
                  </div>
                  {!notif.read && (
                    <button className="p-1 hover:bg-cyber-blue/20 rounded transition-colors">
                      <Check className="w-4 h-4 text-cyber-blue" />
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}

// 公司配置类型
interface CompanyConfig {
  company_name: string
  company_intro: string
  contact_phone: string
  contact_email: string
  contact_wechat: string
  address: string
  products: Array<{ name: string; description: string; features: string[] }>
  service_routes: Array<{ from_location: string; to_location: string; transport: string; time: string; price_ref: string }>
  advantages: string[]
  faq: Array<{ question: string; answer: string }>
  price_policy: string
}

// 设置弹窗
function SettingsModal({ 
  isOpen, 
  onClose 
}: { 
  isOpen: boolean
  onClose: () => void
}) {
  const [activeTab, setActiveTab] = useState<'company' | 'general' | 'api' | 'wechat'>('company')
  const [companyConfig, setCompanyConfig] = useState<CompanyConfig>({
    company_name: '',
    company_intro: '',
    contact_phone: '',
    contact_email: '',
    contact_wechat: '',
    address: '',
    products: [],
    service_routes: [],
    advantages: [],
    faq: [],
    price_policy: ''
  })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [newAdvantage, setNewAdvantage] = useState('')
  
  // 获取公司配置
  useEffect(() => {
    if (isOpen) {
      fetchCompanyConfig()
    }
  }, [isOpen])
  
  const fetchCompanyConfig = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/company/config')
      if (res.ok) {
        const data = await res.json()
        setCompanyConfig(data)
      }
    } catch (error) {
      console.error('获取公司配置失败:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const saveCompanyConfig = async () => {
    setSaving(true)
    try {
      const res = await fetch('/api/company/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(companyConfig)
      })
      if (res.ok) {
        alert('公司配置已保存！AI员工将使用最新配置')
      } else {
        alert('保存失败，请重试')
      }
    } catch (error) {
      console.error('保存公司配置失败:', error)
      alert('保存失败，请检查网络')
    } finally {
      setSaving(false)
    }
  }
  
  // 添加产品
  const addProduct = () => {
    setCompanyConfig({
      ...companyConfig,
      products: [...companyConfig.products, { name: '', description: '', features: [] }]
    })
  }
  
  // 删除产品
  const removeProduct = (index: number) => {
    const newProducts = companyConfig.products.filter((_, i) => i !== index)
    setCompanyConfig({ ...companyConfig, products: newProducts })
  }
  
  // 更新产品
  const updateProduct = (index: number, field: string, value: any) => {
    const newProducts = [...companyConfig.products]
    newProducts[index] = { ...newProducts[index], [field]: value }
    setCompanyConfig({ ...companyConfig, products: newProducts })
  }
  
  // 添加航线
  const addRoute = () => {
    setCompanyConfig({
      ...companyConfig,
      service_routes: [...companyConfig.service_routes, { from_location: '', to_location: '', transport: '海运', time: '', price_ref: '' }]
    })
  }
  
  // 删除航线
  const removeRoute = (index: number) => {
    const newRoutes = companyConfig.service_routes.filter((_, i) => i !== index)
    setCompanyConfig({ ...companyConfig, service_routes: newRoutes })
  }
  
  // 更新航线
  const updateRoute = (index: number, field: string, value: string) => {
    const newRoutes = [...companyConfig.service_routes]
    newRoutes[index] = { ...newRoutes[index], [field]: value }
    setCompanyConfig({ ...companyConfig, service_routes: newRoutes })
  }
  
  // 添加优势
  const addAdvantage = () => {
    if (newAdvantage.trim()) {
      setCompanyConfig({
        ...companyConfig,
        advantages: [...companyConfig.advantages, newAdvantage.trim()]
      })
      setNewAdvantage('')
    }
  }
  
  // 删除优势
  const removeAdvantage = (index: number) => {
    const newAdvantages = companyConfig.advantages.filter((_, i) => i !== index)
    setCompanyConfig({ ...companyConfig, advantages: newAdvantages })
  }
  
  if (!isOpen) return null
  
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
      onClick={onClose}
    >
      <motion.div 
        initial={{ scale: 0.95, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: 20 }}
        className="glass-card w-full max-w-3xl mx-4 max-h-[85vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-cyber-blue" />
            <h2 className="text-lg font-bold">系统设置</h2>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* 标签页 */}
        <div className="flex border-b border-white/10 overflow-x-auto">
          <button 
            onClick={() => setActiveTab('company')}
            className={`px-6 py-3 text-sm transition-colors whitespace-nowrap ${
              activeTab === 'company' 
                ? 'text-cyber-blue border-b-2 border-cyber-blue' 
                : 'text-gray-400 hover:text-white'
            }`}
          >
            公司信息
          </button>
          <button 
            onClick={() => setActiveTab('general')}
            className={`px-6 py-3 text-sm transition-colors whitespace-nowrap ${
              activeTab === 'general' 
                ? 'text-cyber-blue border-b-2 border-cyber-blue' 
                : 'text-gray-400 hover:text-white'
            }`}
          >
            通用设置
          </button>
          <button 
            onClick={() => setActiveTab('api')}
            className={`px-6 py-3 text-sm transition-colors whitespace-nowrap ${
              activeTab === 'api' 
                ? 'text-cyber-blue border-b-2 border-cyber-blue' 
                : 'text-gray-400 hover:text-white'
            }`}
          >
            API配置
          </button>
          <button 
            onClick={() => setActiveTab('wechat')}
            className={`px-6 py-3 text-sm transition-colors whitespace-nowrap ${
              activeTab === 'wechat' 
                ? 'text-cyber-blue border-b-2 border-cyber-blue' 
                : 'text-gray-400 hover:text-white'
            }`}
          >
            微信配置
          </button>
        </div>
        
        {/* 内容 */}
        <div className="p-6 overflow-y-auto max-h-[55vh]">
          {/* 公司信息标签页 */}
          {activeTab === 'company' && (
            <div className="space-y-6">
              {loading ? (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-cyber-blue mx-auto mb-2" />
                  <p className="text-gray-400">加载配置...</p>
                </div>
              ) : (
                <>
                  {/* 基本信息 */}
                  <div className="glass-card p-4">
                    <h4 className="font-medium mb-4 text-cyber-blue flex items-center gap-2">
                      <Building2 className="w-4 h-4" />
                      基本信息
                    </h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-gray-400 text-sm mb-1 block">公司名称</label>
                        <input 
                          type="text"
                          value={companyConfig.company_name}
                          onChange={e => setCompanyConfig({ ...companyConfig, company_name: e.target.value })}
                          className="w-full bg-dark-purple/50 border border-white/10 rounded-lg px-3 py-2 text-sm"
                          placeholder="例：XX国际物流有限公司"
                        />
                      </div>
                      <div>
                        <label className="text-gray-400 text-sm mb-1 block">联系电话</label>
                        <input 
                          type="text"
                          value={companyConfig.contact_phone}
                          onChange={e => setCompanyConfig({ ...companyConfig, contact_phone: e.target.value })}
                          className="w-full bg-dark-purple/50 border border-white/10 rounded-lg px-3 py-2 text-sm"
                          placeholder="例：400-XXX-XXXX"
                        />
                      </div>
                      <div>
                        <label className="text-gray-400 text-sm mb-1 block">客服微信</label>
                        <input 
                          type="text"
                          value={companyConfig.contact_wechat}
                          onChange={e => setCompanyConfig({ ...companyConfig, contact_wechat: e.target.value })}
                          className="w-full bg-dark-purple/50 border border-white/10 rounded-lg px-3 py-2 text-sm"
                          placeholder="例：logistics_service"
                        />
                      </div>
                      <div>
                        <label className="text-gray-400 text-sm mb-1 block">邮箱</label>
                        <input 
                          type="email"
                          value={companyConfig.contact_email}
                          onChange={e => setCompanyConfig({ ...companyConfig, contact_email: e.target.value })}
                          className="w-full bg-dark-purple/50 border border-white/10 rounded-lg px-3 py-2 text-sm"
                          placeholder="例：service@company.com"
                        />
                      </div>
                    </div>
                    <div className="mt-4">
                      <label className="text-gray-400 text-sm mb-1 block">公司简介</label>
                      <textarea 
                        value={companyConfig.company_intro}
                        onChange={e => setCompanyConfig({ ...companyConfig, company_intro: e.target.value })}
                        rows={2}
                        className="w-full bg-dark-purple/50 border border-white/10 rounded-lg px-3 py-2 text-sm"
                        placeholder="简要介绍公司主营业务、成立年限、服务特色等"
                      />
                    </div>
                    <div className="mt-4">
                      <label className="text-gray-400 text-sm mb-1 block">公司地址</label>
                      <input 
                        type="text"
                        value={companyConfig.address}
                        onChange={e => setCompanyConfig({ ...companyConfig, address: e.target.value })}
                        className="w-full bg-dark-purple/50 border border-white/10 rounded-lg px-3 py-2 text-sm"
                        placeholder="例：广东省深圳市南山区XXX大厦"
                      />
                    </div>
                  </div>
                  
                  {/* 产品服务 */}
                  <div className="glass-card p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-medium text-cyber-blue flex items-center gap-2">
                        <Package className="w-4 h-4" />
                        产品与服务
                      </h4>
                      <button 
                        onClick={addProduct}
                        className="text-xs px-3 py-1 bg-cyber-blue/20 text-cyber-blue rounded-lg hover:bg-cyber-blue/30 transition-colors"
                      >
                        + 添加产品
                      </button>
                    </div>
                    
                    {companyConfig.products.length === 0 ? (
                      <p className="text-gray-500 text-sm text-center py-4">暂无产品，点击"添加产品"开始添加</p>
                    ) : (
                      <div className="space-y-3">
                        {companyConfig.products.map((product, index) => (
                          <div key={index} className="bg-dark-purple/30 p-3 rounded-lg">
                            <div className="flex items-center gap-2 mb-2">
                              <input 
                                type="text"
                                value={product.name}
                                onChange={e => updateProduct(index, 'name', e.target.value)}
                                className="flex-1 bg-dark-purple/50 border border-white/10 rounded px-2 py-1 text-sm"
                                placeholder="产品名称"
                              />
                              <button 
                                onClick={() => removeProduct(index)}
                                className="text-alert-red hover:bg-alert-red/20 p-1 rounded"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                            <input 
                              type="text"
                              value={product.description}
                              onChange={e => updateProduct(index, 'description', e.target.value)}
                              className="w-full bg-dark-purple/50 border border-white/10 rounded px-2 py-1 text-sm mb-2"
                              placeholder="产品描述"
                            />
                            <input 
                              type="text"
                              value={product.features.join(', ')}
                              onChange={e => updateProduct(index, 'features', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                              className="w-full bg-dark-purple/50 border border-white/10 rounded px-2 py-1 text-sm"
                              placeholder="特点（用逗号分隔）"
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  {/* 服务航线 */}
                  <div className="glass-card p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-medium text-cyber-blue flex items-center gap-2">
                        <Globe className="w-4 h-4" />
                        服务航线
                      </h4>
                      <button 
                        onClick={addRoute}
                        className="text-xs px-3 py-1 bg-cyber-blue/20 text-cyber-blue rounded-lg hover:bg-cyber-blue/30 transition-colors"
                      >
                        + 添加航线
                      </button>
                    </div>
                    
                    {companyConfig.service_routes.length === 0 ? (
                      <p className="text-gray-500 text-sm text-center py-4">暂无航线，点击"添加航线"开始添加</p>
                    ) : (
                      <div className="space-y-3">
                        {companyConfig.service_routes.map((route, index) => (
                          <div key={index} className="bg-dark-purple/30 p-3 rounded-lg">
                            <div className="grid grid-cols-6 gap-2 items-center">
                              <input 
                                type="text"
                                value={route.from_location}
                                onChange={e => updateRoute(index, 'from_location', e.target.value)}
                                className="bg-dark-purple/50 border border-white/10 rounded px-2 py-1 text-sm"
                                placeholder="起运地"
                              />
                              <span className="text-center text-gray-500">→</span>
                              <input 
                                type="text"
                                value={route.to_location}
                                onChange={e => updateRoute(index, 'to_location', e.target.value)}
                                className="bg-dark-purple/50 border border-white/10 rounded px-2 py-1 text-sm"
                                placeholder="目的地"
                              />
                              <select 
                                value={route.transport}
                                onChange={e => updateRoute(index, 'transport', e.target.value)}
                                className="bg-dark-purple/50 border border-white/10 rounded px-2 py-1 text-sm"
                              >
                                <option value="海运">海运</option>
                                <option value="空运">空运</option>
                                <option value="铁路">铁路</option>
                                <option value="快递">快递</option>
                              </select>
                              <input 
                                type="text"
                                value={route.time}
                                onChange={e => updateRoute(index, 'time', e.target.value)}
                                className="bg-dark-purple/50 border border-white/10 rounded px-2 py-1 text-sm"
                                placeholder="时效"
                              />
                              <button 
                                onClick={() => removeRoute(index)}
                                className="text-alert-red hover:bg-alert-red/20 p-1 rounded justify-self-end"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                            <input 
                              type="text"
                              value={route.price_ref}
                              onChange={e => updateRoute(index, 'price_ref', e.target.value)}
                              className="w-full bg-dark-purple/50 border border-white/10 rounded px-2 py-1 text-sm mt-2"
                              placeholder="参考价格（可选，如：$2000/TEU）"
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  {/* 公司优势 */}
                  <div className="glass-card p-4">
                    <h4 className="font-medium mb-4 text-cyber-blue flex items-center gap-2">
                      <Star className="w-4 h-4" />
                      公司优势
                    </h4>
                    <div className="flex flex-wrap gap-2 mb-3">
                      {companyConfig.advantages.map((adv, index) => (
                        <span key={index} className="px-3 py-1 bg-cyber-green/20 text-cyber-green text-sm rounded-full flex items-center gap-1">
                          {adv}
                          <button onClick={() => removeAdvantage(index)} className="hover:text-alert-red">
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input 
                        type="text"
                        value={newAdvantage}
                        onChange={e => setNewAdvantage(e.target.value)}
                        onKeyPress={e => e.key === 'Enter' && addAdvantage()}
                        className="flex-1 bg-dark-purple/50 border border-white/10 rounded-lg px-3 py-2 text-sm"
                        placeholder="输入优势特点，按回车添加"
                      />
                      <button 
                        onClick={addAdvantage}
                        className="px-4 py-2 bg-cyber-blue/20 text-cyber-blue rounded-lg hover:bg-cyber-blue/30 transition-colors text-sm"
                      >
                        添加
                      </button>
                    </div>
                  </div>
                  
                  {/* 价格政策 */}
                  <div className="glass-card p-4">
                    <h4 className="font-medium mb-4 text-cyber-blue flex items-center gap-2">
                      <DollarSign className="w-4 h-4" />
                      价格政策
                    </h4>
                    <textarea 
                      value={companyConfig.price_policy}
                      onChange={e => setCompanyConfig({ ...companyConfig, price_policy: e.target.value })}
                      rows={2}
                      className="w-full bg-dark-purple/50 border border-white/10 rounded-lg px-3 py-2 text-sm"
                      placeholder="描述您的报价策略，如：根据货量、季节、航线综合报价，量大从优..."
                    />
                  </div>
                  
                  {/* 保存按钮 */}
                  <div className="flex justify-end gap-3">
                    <button 
                      onClick={fetchCompanyConfig}
                      className="px-4 py-2 glass-card hover:border-white/30 transition-colors text-sm"
                    >
                      重置
                    </button>
                    <button 
                      onClick={saveCompanyConfig}
                      disabled={saving}
                      className="px-6 py-2 bg-cyber-blue text-white rounded-lg hover:bg-cyber-blue/80 transition-colors text-sm flex items-center gap-2"
                    >
                      {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                      保存配置
                    </button>
                  </div>
                  
                  <p className="text-gray-500 text-xs text-center">
                    💡 保存后，AI员工（小销、小文等）在与客户对话和生成内容时会使用这些信息
                  </p>
                </>
              )}
            </div>
          )}
          
          {activeTab === 'general' && (
            <div className="space-y-6">
              <div className="glass-card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">自动刷新</p>
                    <p className="text-gray-400 text-sm">控制面板数据自动刷新间隔</p>
                  </div>
                  <select className="bg-dark-purple/50 border border-white/10 rounded-lg px-3 py-2 text-sm">
                    <option value="15">15秒</option>
                    <option value="30">30秒</option>
                    <option value="60">1分钟</option>
                  </select>
                </div>
              </div>
              
              <div className="glass-card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">通知提醒</p>
                    <p className="text-gray-400 text-sm">新客户或高意向客户提醒</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" defaultChecked />
                    <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyber-blue"></div>
                  </label>
                </div>
              </div>
              
              <div className="glass-card p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">数据统计</p>
                    <p className="text-gray-400 text-sm">查看系统运行状态</p>
                  </div>
                  <Link 
                    href="/team"
                    className="text-cyber-blue hover:underline flex items-center gap-1 text-sm"
                  >
                    查看详情 <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            </div>
          )}
          
          {activeTab === 'api' && (
            <div className="space-y-6">
              <div className="glass-card p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Key className="w-4 h-4 text-cyber-blue" />
                  <p className="font-medium">通义千问 API</p>
                </div>
                <p className="text-gray-400 text-sm mb-3">用于AI对话和文案生成</p>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-1 bg-cyber-green/20 text-cyber-green text-xs rounded">已配置</span>
                  <span className="text-gray-500 text-xs">sk-b7ea...1c</span>
                </div>
              </div>
              
              <div className="glass-card p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Video className="w-4 h-4 text-neon-purple" />
                  <p className="font-medium">可灵 AI (中国版)</p>
                </div>
                <p className="text-gray-400 text-sm mb-3">用于AI视频生成</p>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-1 bg-cyber-green/20 text-cyber-green text-xs rounded">已配置</span>
                  <span className="text-gray-500 text-xs">api-beijing.klingai.com</span>
                </div>
              </div>
              
              <div className="glass-card p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Database className="w-4 h-4 text-energy-orange" />
                  <p className="font-medium">数据库</p>
                </div>
                <p className="text-gray-400 text-sm mb-3">PostgreSQL 数据存储</p>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-1 bg-cyber-green/20 text-cyber-green text-xs rounded">已连接</span>
                  <span className="text-gray-500 text-xs">localhost:5432</span>
                </div>
              </div>
              
              <p className="text-gray-500 text-xs text-center">
                API配置需要在服务器 .env 文件中修改
              </p>
            </div>
          )}
          
          {activeTab === 'wechat' && (
            <div className="space-y-6">
              <div className="glass-card p-4">
                <div className="flex items-center gap-2 mb-3">
                  <MessageSquare className="w-4 h-4 text-cyber-green" />
                  <p className="font-medium">企业微信配置</p>
                </div>
                <p className="text-gray-400 text-sm mb-3">用于接收和发送客户消息</p>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-1 bg-energy-orange/20 text-energy-orange text-xs rounded">待配置</span>
                </div>
              </div>
              
              <div className="glass-card p-4 border-dashed">
                <h4 className="font-medium mb-2">配置步骤：</h4>
                <ol className="text-gray-400 text-sm space-y-2 list-decimal list-inside">
                  <li>登录企业微信管理后台</li>
                  <li>创建应用获取 CorpID 和 Secret</li>
                  <li>配置消息接收服务器URL</li>
                  <li>在服务器 .env 文件中填写配置</li>
                </ol>
              </div>
              
              <a 
                href="https://work.weixin.qq.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="block text-center py-3 glass-card hover:border-cyber-blue/50 transition-colors text-cyber-blue"
              >
                打开企业微信管理后台 <ExternalLink className="w-4 h-4 inline ml-1" />
              </a>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}

// 统计卡片组件
function StatCard({ 
  title, 
  value, 
  change, 
  icon: Icon,
  color = 'cyber-blue'
}: {
  title: string
  value: string | number
  change?: string
  icon: any
  color?: string
}) {
  return (
    <motion.div 
      variants={itemVariants}
      className="glass-card-hover p-6"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-gray-400 text-sm mb-1">{title}</p>
          <p className={`text-3xl font-bold font-number text-${color}`}>{value}</p>
          {change && (
            <p className="text-cyber-green text-sm mt-1">{change}</p>
          )}
        </div>
        <div className={`p-3 rounded-lg bg-${color}/10`}>
          <Icon className={`w-6 h-6 text-${color}`} />
        </div>
      </div>
    </motion.div>
  )
}

// AI员工卡片组件
function AgentCard({ 
  name, 
  role, 
  status, 
  tasksToday 
}: {
  name: string
  role: string
  status: 'online' | 'busy' | 'offline'
  tasksToday: number
}) {
  const statusConfig = {
    online: { label: '在线', class: 'badge-online', glow: 'shadow-cyber' },
    busy: { label: '忙碌', class: 'badge-busy', glow: 'shadow-[0_0_15px_rgba(255,107,53,0.3)]' },
    offline: { label: '离线', class: 'badge-offline', glow: '' }
  }
  
  const config = statusConfig[status]
  
  return (
    <Link href="/team">
      <motion.div 
        variants={itemVariants}
        whileHover={{ scale: 1.02 }}
        className={`glass-card p-4 cursor-pointer transition-all ${config.glow}`}
      >
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyber-blue to-neon-purple flex items-center justify-center text-lg font-bold">
            {name[0]}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-medium">{name}</span>
              <span className={config.class}>{config.label}</span>
            </div>
            <p className="text-gray-400 text-sm">{role}</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-number font-bold text-cyber-blue">{tasksToday}</p>
            <p className="text-gray-500 text-xs">今日任务</p>
          </div>
        </div>
      </motion.div>
    </Link>
  )
}

// 活动项组件
function ActivityItem({ 
  agent, 
  action, 
  time,
  highlight = false
}: {
  agent: string
  action: string
  time: string
  highlight?: boolean
}) {
  return (
    <motion.div 
      variants={itemVariants}
      className={`flex items-center gap-3 p-3 rounded-lg ${
        highlight ? 'bg-cyber-green/10 border border-cyber-green/30' : 'hover:bg-white/5'
      } transition-colors`}
    >
      <div className={`w-2 h-2 rounded-full ${highlight ? 'bg-cyber-green animate-pulse' : 'bg-gray-500'}`} />
      <span className="text-cyber-blue font-medium">[{agent}]</span>
      <span className="flex-1 text-gray-300 truncate">{action}</span>
      <span className="text-gray-500 text-sm">{time}</span>
    </motion.div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState({
    newCustomers: 0,
    highIntent: 0,
    conversations: 0,
    videos: 0,
    processing: 0
  })
  
  const [agents, setAgents] = useState([
    { name: '小调', role: '调度主管', status: 'online' as const, tasksToday: 0 },
    { name: '小销', role: '销售客服', status: 'online' as const, tasksToday: 0 },
    { name: '小析', role: '客户分析', status: 'online' as const, tasksToday: 0 },
    { name: '小文', role: '文案策划', status: 'online' as const, tasksToday: 0 },
    { name: '小视', role: '视频创作', status: 'online' as const, tasksToday: 0 },
    { name: '小跟', role: '跟进专员', status: 'online' as const, tasksToday: 0 },
  ])
  
  const [activities, setActivities] = useState<Array<{agent: string; action: string; time: string; highlight: boolean}>>([])
  const [loading, setLoading] = useState(true)
  
  // 通知和设置状态
  const [showNotifications, setShowNotifications] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [notifications, setNotifications] = useState<Array<{ id: string; title: string; content: string; time: string; read: boolean }>>([])
  const [mounted, setMounted] = useState(false)
  
  // 客户端挂载后初始化通知（避免水合错误）
  useEffect(() => {
    setMounted(true)
    setNotifications([
      { id: '1', title: '系统已就绪', content: 'AI员工团队已上线，等待客户对话', time: '刚刚', read: false },
      { id: '2', title: '视频生成完成', content: '物流服务宣传视频已生成成功', time: '5分钟前', read: true },
    ])
  }, [])
  
  const unreadCount = notifications.filter(n => !n.read).length
  
  // 获取真实数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 获取统计数据
        const statsRes = await fetch('/api/dashboard/stats')
        if (statsRes.ok) {
          const statsData = await statsRes.json()
          setStats({
            newCustomers: statsData.today?.new_customers || 0,
            highIntent: statsData.today?.high_intent_customers || 0,
            conversations: statsData.today?.conversations || 0,
            videos: statsData.today?.videos_generated || 0,
            processing: statsData.today?.processing_tasks || 0
          })
        }
        
        // 获取AI团队状态
        const teamRes = await fetch('/api/dashboard/team-status')
        if (teamRes.ok) {
          const teamData = await teamRes.json()
          if (teamData.agents && teamData.agents.length > 0) {
            const agentMap: Record<string, any> = {}
            teamData.agents.forEach((a: any) => {
              agentMap[a.name] = a
            })
            setAgents(prev => prev.map(agent => ({
              ...agent,
              status: agentMap[agent.name]?.status || 'online',
              tasksToday: agentMap[agent.name]?.tasks_today || 0
            })))
          }
        }
        
        // 获取最近活动
        const activitiesRes = await fetch('/api/dashboard/recent-activities')
        if (activitiesRes.ok) {
          const activitiesData = await activitiesRes.json()
          if (activitiesData.activities && activitiesData.activities.length > 0) {
            setActivities(activitiesData.activities.map((a: any, i: number) => ({
              agent: a.agent || '系统',
              action: a.content_preview || a.action || '活动记录',
              time: formatTime(a.timestamp),
              highlight: i === 0
            })))
          } else {
            setActivities([{ agent: '系统', action: '暂无活动记录', time: '刚刚', highlight: false }])
          }
        }
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])
  
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
    if (diff < 60) return '刚刚'
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
    return `${Math.floor(diff / 86400)}天前`
  }
  
  const handleMarkRead = (id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
  }
  
  const handleClearAll = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))
  }
  
  return (
    <div className="min-h-screen p-6">
      {/* 顶部导航 */}
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-tech font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-neon-purple">
            AI获客控制中心
          </h1>
          <p className="text-gray-400 mt-1">物流行业智能获客系统</p>
        </div>
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setShowNotifications(true)}
            className="p-2 glass-card hover:border-cyber-blue/50 transition-colors relative"
          >
            <Bell className="w-5 h-5 text-gray-400" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-alert-red text-white text-xs rounded-full flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </button>
          <button 
            onClick={() => setShowSettings(true)}
            className="p-2 glass-card hover:border-cyber-blue/50 transition-colors"
          >
            <Settings className="w-5 h-5 text-gray-400" />
          </button>
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyber-blue to-neon-purple flex items-center justify-center font-bold">
            A
          </div>
        </div>
      </header>
      
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="space-y-6"
      >
        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            title="今日新客户" 
            value={stats.newCustomers}
            icon={Users}
            color="cyber-blue"
          />
          <StatCard 
            title="高意向客户" 
            value={stats.highIntent}
            icon={TrendingUp}
            color="cyber-green"
          />
          <StatCard 
            title="对话总数" 
            value={stats.conversations}
            icon={MessageSquare}
            color="neon-purple"
          />
          <StatCard 
            title="视频生成" 
            value={stats.videos}
            change={stats.processing > 0 ? `${stats.processing} 处理中` : undefined}
            icon={Video}
            color="energy-orange"
          />
        </div>
        
        {/* 主内容区 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* AI团队状态 */}
          <motion.div variants={itemVariants} className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Bot className="w-5 h-5 text-cyber-blue" />
                AI员工团队
              </h2>
              <Link 
                href="/team" 
                className="text-cyber-blue hover:text-cyber-blue/80 flex items-center gap-1 text-sm"
              >
                查看详情 <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {agents.map((agent) => (
                <AgentCard key={agent.name} {...agent} />
              ))}
            </div>
          </motion.div>
          
          {/* 实时活动 */}
          <motion.div variants={itemVariants}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">实时动态</h2>
              <span className="text-gray-500 text-sm">自动刷新</span>
            </div>
            <div className="glass-card p-4 space-y-2">
              {activities.map((activity, index) => (
                <ActivityItem key={index} {...activity} />
              ))}
            </div>
          </motion.div>
        </div>
        
        {/* 快捷操作 */}
        <motion.div variants={itemVariants}>
          <h2 className="text-xl font-bold mb-4">快捷操作</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Link href="/videos/create" className="btn-cyber text-center py-4">
              <Video className="w-5 h-5 mx-auto mb-2" />
              生成视频
            </Link>
            <Link href="/customers" className="btn-cyber text-center py-4">
              <Users className="w-5 h-5 mx-auto mb-2" />
              客户列表
            </Link>
            <Link href="/conversations" className="btn-cyber text-center py-4">
              <MessageSquare className="w-5 h-5 mx-auto mb-2" />
              对话记录
            </Link>
            <Link href="/team" className="btn-cyber text-center py-4">
              <Bot className="w-5 h-5 mx-auto mb-2" />
              AI团队
            </Link>
          </div>
        </motion.div>
      </motion.div>
      
      {/* 通知弹窗 */}
      <AnimatePresence>
        {showNotifications && (
          <NotificationsModal 
            isOpen={showNotifications}
            onClose={() => setShowNotifications(false)}
            notifications={notifications}
            onMarkRead={handleMarkRead}
            onClearAll={handleClearAll}
          />
        )}
      </AnimatePresence>
      
      {/* 设置弹窗 */}
      <AnimatePresence>
        {showSettings && (
          <SettingsModal 
            isOpen={showSettings}
            onClose={() => setShowSettings(false)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
