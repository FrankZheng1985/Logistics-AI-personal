<?php
/**
 * Template Name: 关于我们页面
 * 
 * 公司简介、发展历程、团队介绍
 *
 * @package Sysafari_Logistics
 */

get_header();
?>

<div class="page-header">
    <div class="container">
        <h1><?php esc_html_e('关于我们', 'sysafari-logistics'); ?></h1>
    </div>
</div>

<?php sysafari_breadcrumbs(); ?>

<section class="section page-content">
    <div class="container">
        
        <!-- 公司简介 -->
        <div class="about-intro" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-2xl); align-items: center; margin-bottom: var(--spacing-3xl);">
            <div class="about-text">
                <h2 style="margin-bottom: var(--spacing-lg);"><?php esc_html_e('专业的国际物流服务商', 'sysafari-logistics'); ?></h2>
                <p style="color: var(--color-gray-dark); line-height: 1.8; margin-bottom: var(--spacing-md);">
                    <?php esc_html_e('我们是一家专注于国际物流服务的企业，致力于为全球客户提供海运、空运、陆运、仓储等一站式物流解决方案。自成立以来，我们始终秉承"专业、高效、可靠"的服务理念，为数千家企业提供了优质的物流服务。', 'sysafari-logistics'); ?>
                </p>
                <p style="color: var(--color-gray-dark); line-height: 1.8; margin-bottom: var(--spacing-md);">
                    <?php esc_html_e('凭借全球化的物流网络、专业的服务团队和先进的信息技术，我们能够为客户提供定制化的物流方案，满足各类货运需求。无论是跨境电商物流、大宗货物运输，还是供应链管理，我们都能为您提供最优质的服务。', 'sysafari-logistics'); ?>
                </p>
                <div style="display: flex; gap: var(--spacing-lg); margin-top: var(--spacing-xl);">
                    <a href="<?php echo esc_url(home_url('/contact')); ?>" class="btn btn-secondary">
                        <?php esc_html_e('联系我们', 'sysafari-logistics'); ?>
                    </a>
                    <a href="<?php echo esc_url(home_url('/services')); ?>" class="btn btn-outline">
                        <?php esc_html_e('了解服务', 'sysafari-logistics'); ?>
                    </a>
                </div>
            </div>
            <div class="about-image" style="background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%); border-radius: var(--radius-lg); height: 400px; display: flex; align-items: center; justify-content: center;">
                <i class="fas fa-globe-asia" style="font-size: 8rem; color: rgba(255,255,255,0.3);"></i>
            </div>
        </div>
        
        <!-- 核心数据 -->
        <div class="about-stats" style="background: var(--color-light); border-radius: var(--radius-lg); padding: var(--spacing-2xl); margin-bottom: var(--spacing-3xl);">
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--spacing-xl); text-align: center;">
                <div class="stat-item">
                    <div class="stat-number" style="font-size: 3rem; font-weight: 700; color: var(--color-secondary);">15+</div>
                    <div class="stat-label" style="color: var(--color-gray-dark);"><?php esc_html_e('年行业经验', 'sysafari-logistics'); ?></div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" style="font-size: 3rem; font-weight: 700; color: var(--color-secondary);">220+</div>
                    <div class="stat-label" style="color: var(--color-gray-dark);"><?php esc_html_e('覆盖国家/地区', 'sysafari-logistics'); ?></div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" style="font-size: 3rem; font-weight: 700; color: var(--color-secondary);">5000+</div>
                    <div class="stat-label" style="color: var(--color-gray-dark);"><?php esc_html_e('服务客户', 'sysafari-logistics'); ?></div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" style="font-size: 3rem; font-weight: 700; color: var(--color-secondary);">99%</div>
                    <div class="stat-label" style="color: var(--color-gray-dark);"><?php esc_html_e('客户满意度', 'sysafari-logistics'); ?></div>
                </div>
            </div>
        </div>
        
        <!-- 发展历程 -->
        <div class="about-timeline" style="margin-bottom: var(--spacing-3xl);">
            <h2 style="text-align: center; margin-bottom: var(--spacing-2xl);"><?php esc_html_e('发展历程', 'sysafari-logistics'); ?></h2>
            
            <div class="timeline" style="position: relative; max-width: 800px; margin: 0 auto;">
                <div class="timeline-line" style="position: absolute; left: 50%; top: 0; bottom: 0; width: 2px; background: var(--color-gray-light); transform: translateX(-50%);"></div>
                
                <div class="timeline-item" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-xl); margin-bottom: var(--spacing-xl); position: relative;">
                    <div style="text-align: right; padding-right: var(--spacing-xl);">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--color-secondary);">2008</div>
                        <h4><?php esc_html_e('公司成立', 'sysafari-logistics'); ?></h4>
                        <p style="color: var(--color-gray-dark);"><?php esc_html_e('在深圳创立，专注于国际海运业务', 'sysafari-logistics'); ?></p>
                    </div>
                    <div style="position: absolute; left: 50%; top: 0; width: 16px; height: 16px; background: var(--color-primary); border-radius: 50%; transform: translateX(-50%); border: 3px solid white; box-shadow: var(--shadow-md);"></div>
                    <div></div>
                </div>
                
                <div class="timeline-item" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-xl); margin-bottom: var(--spacing-xl); position: relative;">
                    <div></div>
                    <div style="position: absolute; left: 50%; top: 0; width: 16px; height: 16px; background: var(--color-primary); border-radius: 50%; transform: translateX(-50%); border: 3px solid white; box-shadow: var(--shadow-md);"></div>
                    <div style="padding-left: var(--spacing-xl);">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--color-secondary);">2012</div>
                        <h4><?php esc_html_e('业务拓展', 'sysafari-logistics'); ?></h4>
                        <p style="color: var(--color-gray-dark);"><?php esc_html_e('新增空运业务，服务范围扩展至50个国家', 'sysafari-logistics'); ?></p>
                    </div>
                </div>
                
                <div class="timeline-item" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-xl); margin-bottom: var(--spacing-xl); position: relative;">
                    <div style="text-align: right; padding-right: var(--spacing-xl);">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--color-secondary);">2016</div>
                        <h4><?php esc_html_e('全球布局', 'sysafari-logistics'); ?></h4>
                        <p style="color: var(--color-gray-dark);"><?php esc_html_e('建立海外仓储网络，覆盖欧美主要市场', 'sysafari-logistics'); ?></p>
                    </div>
                    <div style="position: absolute; left: 50%; top: 0; width: 16px; height: 16px; background: var(--color-primary); border-radius: 50%; transform: translateX(-50%); border: 3px solid white; box-shadow: var(--shadow-md);"></div>
                    <div></div>
                </div>
                
                <div class="timeline-item" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-xl); margin-bottom: var(--spacing-xl); position: relative;">
                    <div></div>
                    <div style="position: absolute; left: 50%; top: 0; width: 16px; height: 16px; background: var(--color-primary); border-radius: 50%; transform: translateX(-50%); border: 3px solid white; box-shadow: var(--shadow-md);"></div>
                    <div style="padding-left: var(--spacing-xl);">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--color-secondary);">2020</div>
                        <h4><?php esc_html_e('数字化升级', 'sysafari-logistics'); ?></h4>
                        <p style="color: var(--color-gray-dark);"><?php esc_html_e('引入智能物流系统，实现全程可视化追踪', 'sysafari-logistics'); ?></p>
                    </div>
                </div>
                
                <div class="timeline-item" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-xl); position: relative;">
                    <div style="text-align: right; padding-right: var(--spacing-xl);">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--color-secondary);">2024</div>
                        <h4><?php esc_html_e('AI赋能', 'sysafari-logistics'); ?></h4>
                        <p style="color: var(--color-gray-dark);"><?php esc_html_e('AI智能客服上线，为客户提供7x24小时服务', 'sysafari-logistics'); ?></p>
                    </div>
                    <div style="position: absolute; left: 50%; top: 0; width: 16px; height: 16px; background: var(--color-secondary); border-radius: 50%; transform: translateX(-50%); border: 3px solid white; box-shadow: var(--shadow-md);"></div>
                    <div></div>
                </div>
            </div>
        </div>
        
        <!-- 核心价值观 -->
        <div class="about-values" style="margin-bottom: var(--spacing-3xl);">
            <h2 style="text-align: center; margin-bottom: var(--spacing-2xl);"><?php esc_html_e('核心价值观', 'sysafari-logistics'); ?></h2>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--spacing-lg);">
                <div class="value-card" style="background: var(--color-white); border: 1px solid var(--color-gray-light); border-radius: var(--radius-lg); padding: var(--spacing-xl); text-align: center; transition: all var(--transition-normal);">
                    <div style="width: 80px; height: 80px; background: var(--color-primary-light); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto var(--spacing-md);">
                        <i class="fas fa-handshake" style="font-size: 2rem; color: var(--color-secondary);"></i>
                    </div>
                    <h3><?php esc_html_e('诚信为本', 'sysafari-logistics'); ?></h3>
                    <p style="color: var(--color-gray-dark);"><?php esc_html_e('以诚信赢得客户信任，以专业创造客户价值', 'sysafari-logistics'); ?></p>
                </div>
                
                <div class="value-card" style="background: var(--color-white); border: 1px solid var(--color-gray-light); border-radius: var(--radius-lg); padding: var(--spacing-xl); text-align: center; transition: all var(--transition-normal);">
                    <div style="width: 80px; height: 80px; background: var(--color-primary-light); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto var(--spacing-md);">
                        <i class="fas fa-rocket" style="font-size: 2rem; color: var(--color-secondary);"></i>
                    </div>
                    <h3><?php esc_html_e('持续创新', 'sysafari-logistics'); ?></h3>
                    <p style="color: var(--color-gray-dark);"><?php esc_html_e('拥抱变化，不断创新，为客户提供更好的服务', 'sysafari-logistics'); ?></p>
                </div>
                
                <div class="value-card" style="background: var(--color-white); border: 1px solid var(--color-gray-light); border-radius: var(--radius-lg); padding: var(--spacing-xl); text-align: center; transition: all var(--transition-normal);">
                    <div style="width: 80px; height: 80px; background: var(--color-primary-light); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto var(--spacing-md);">
                        <i class="fas fa-users" style="font-size: 2rem; color: var(--color-secondary);"></i>
                    </div>
                    <h3><?php esc_html_e('客户至上', 'sysafari-logistics'); ?></h3>
                    <p style="color: var(--color-gray-dark);"><?php esc_html_e('以客户需求为中心，提供超越期望的服务体验', 'sysafari-logistics'); ?></p>
                </div>
            </div>
        </div>
        
        <!-- 资质证书 -->
        <div class="about-certifications">
            <h2 style="text-align: center; margin-bottom: var(--spacing-2xl);"><?php esc_html_e('资质证书', 'sysafari-logistics'); ?></h2>
            
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--spacing-lg); text-align: center;">
                <div class="cert-item" style="padding: var(--spacing-lg);">
                    <i class="fas fa-certificate" style="font-size: 3rem; color: var(--color-primary); margin-bottom: var(--spacing-md);"></i>
                    <p><?php esc_html_e('ISO 9001质量认证', 'sysafari-logistics'); ?></p>
                </div>
                <div class="cert-item" style="padding: var(--spacing-lg);">
                    <i class="fas fa-award" style="font-size: 3rem; color: var(--color-primary); margin-bottom: var(--spacing-md);"></i>
                    <p><?php esc_html_e('AAAA级物流企业', 'sysafari-logistics'); ?></p>
                </div>
                <div class="cert-item" style="padding: var(--spacing-lg);">
                    <i class="fas fa-shield-alt" style="font-size: 3rem; color: var(--color-primary); margin-bottom: var(--spacing-md);"></i>
                    <p><?php esc_html_e('AEO高级认证', 'sysafari-logistics'); ?></p>
                </div>
                <div class="cert-item" style="padding: var(--spacing-lg);">
                    <i class="fas fa-check-circle" style="font-size: 3rem; color: var(--color-primary); margin-bottom: var(--spacing-md);"></i>
                    <p><?php esc_html_e('无船承运人资质', 'sysafari-logistics'); ?></p>
                </div>
            </div>
        </div>
        
    </div>
</section>

<style>
.value-card:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-lg);
    border-color: var(--color-primary);
}

@media (max-width: 1024px) {
    .about-intro {
        grid-template-columns: 1fr !important;
    }
    
    .about-stats > div {
        grid-template-columns: repeat(2, 1fr) !important;
    }
}

@media (max-width: 768px) {
    .about-stats > div {
        grid-template-columns: 1fr !important;
    }
    
    .about-values > div,
    .about-certifications > div:last-child {
        grid-template-columns: 1fr !important;
    }
    
    .timeline-item {
        grid-template-columns: 1fr !important;
    }
    
    .timeline-item > div:first-child {
        text-align: left !important;
        padding-right: 0 !important;
        padding-left: var(--spacing-xl) !important;
    }
    
    .timeline-line {
        left: 8px !important;
    }
    
    .timeline-item > div[style*="position: absolute"] {
        left: 8px !important;
    }
}
</style>

<?php
get_footer();
