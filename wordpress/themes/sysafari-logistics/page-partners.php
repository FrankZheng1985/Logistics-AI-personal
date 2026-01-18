<?php
/**
 * Template Name: 合作伙伴页面
 * 
 * 展示合作伙伴和客户案例
 *
 * @package Sysafari_Logistics
 */

get_header();
?>

<div class="page-header">
    <div class="container">
        <h1><?php esc_html_e('合作伙伴', 'sysafari-logistics'); ?></h1>
    </div>
</div>

<?php sysafari_breadcrumbs(); ?>

<section class="section page-content">
    <div class="container">
        
        <!-- 简介 -->
        <div class="partners-intro" style="text-align: center; max-width: 800px; margin: 0 auto var(--spacing-3xl);">
            <h2 style="margin-bottom: var(--spacing-md);"><?php esc_html_e('携手共赢，共创未来', 'sysafari-logistics'); ?></h2>
            <p style="color: var(--color-gray-dark); font-size: 1.125rem; line-height: 1.8;">
                <?php esc_html_e('我们与全球众多知名企业建立了长期稳定的合作关系，为各行各业客户提供专业的物流服务。感谢每一位合作伙伴的信任与支持。', 'sysafari-logistics'); ?>
            </p>
        </div>
        
        <!-- 合作行业 -->
        <div class="partner-industries" style="margin-bottom: var(--spacing-3xl);">
            <h2 style="text-align: center; margin-bottom: var(--spacing-2xl);"><?php esc_html_e('服务行业', 'sysafari-logistics'); ?></h2>
            
            <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: var(--spacing-lg);">
                <?php
                $industries = array(
                    array('icon' => 'laptop', 'name' => '电子科技'),
                    array('icon' => 'tshirt', 'name' => '服装纺织'),
                    array('icon' => 'car', 'name' => '汽车配件'),
                    array('icon' => 'couch', 'name' => '家居建材'),
                    array('icon' => 'pills', 'name' => '医药健康'),
                    array('icon' => 'utensils', 'name' => '食品饮料'),
                    array('icon' => 'industry', 'name' => '机械设备'),
                    array('icon' => 'gem', 'name' => '珠宝首饰'),
                    array('icon' => 'baby', 'name' => '母婴用品'),
                    array('icon' => 'gamepad', 'name' => '玩具礼品'),
                    array('icon' => 'book', 'name' => '图书文具'),
                    array('icon' => 'box-open', 'name' => '跨境电商'),
                );
                
                foreach ($industries as $industry) :
                ?>
                    <div class="industry-item" style="text-align: center; padding: var(--spacing-lg); background: var(--color-white); border: 1px solid var(--color-gray-light); border-radius: var(--radius-md); transition: all var(--transition-normal);">
                        <i class="fas fa-<?php echo esc_attr($industry['icon']); ?>" style="font-size: 2rem; color: var(--color-secondary); margin-bottom: var(--spacing-sm);"></i>
                        <p style="margin: 0; font-weight: 500;"><?php echo esc_html($industry['name']); ?></p>
                    </div>
                <?php endforeach; ?>
            </div>
        </div>
        
        <!-- 合作伙伴Logo -->
        <div class="partner-logos" style="margin-bottom: var(--spacing-3xl);">
            <h2 style="text-align: center; margin-bottom: var(--spacing-2xl);"><?php esc_html_e('部分合作伙伴', 'sysafari-logistics'); ?></h2>
            
            <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--spacing-lg);">
                <?php for ($i = 1; $i <= 10; $i++) : ?>
                    <div class="partner-logo" style="aspect-ratio: 3/2; background: var(--color-light); border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; padding: var(--spacing-md);">
                        <div style="text-align: center; color: var(--color-gray);">
                            <i class="fas fa-building" style="font-size: 2rem;"></i>
                            <p style="margin: var(--spacing-sm) 0 0; font-size: 0.875rem;">合作伙伴 <?php echo $i; ?></p>
                        </div>
                    </div>
                <?php endfor; ?>
            </div>
            
            <p style="text-align: center; color: var(--color-gray); margin-top: var(--spacing-lg);">
                <?php esc_html_e('* 部分合作伙伴展示，排名不分先后', 'sysafari-logistics'); ?>
            </p>
        </div>
        
        <!-- 客户评价 -->
        <div class="partner-testimonials" style="background: var(--color-light); border-radius: var(--radius-lg); padding: var(--spacing-2xl); margin-bottom: var(--spacing-3xl);">
            <h2 style="text-align: center; margin-bottom: var(--spacing-2xl);"><?php esc_html_e('客户评价', 'sysafari-logistics'); ?></h2>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--spacing-lg);">
                <?php
                $testimonials = array(
                    array(
                        'content' => '作为跨境电商卖家，物流时效对我们至关重要。与Sysafari合作以来，订单派送准时率提升了20%，客户满意度大幅提高。',
                        'author' => '李总',
                        'company' => '某跨境电商公司',
                    ),
                    array(
                        'content' => '专业的团队，高效的服务。他们不仅帮我们解决了复杂的报关问题，还提供了很多供应链优化建议，是值得信赖的合作伙伴。',
                        'author' => '王经理',
                        'company' => '某制造企业',
                    ),
                    array(
                        'content' => '多年来一直合作，服务始终如一。无论是日常货运还是紧急订单，他们都能很好地完成。强烈推荐！',
                        'author' => '张总',
                        'company' => '某贸易公司',
                    ),
                );
                
                foreach ($testimonials as $testimonial) :
                ?>
                    <div class="testimonial-card" style="background: var(--color-white); border-radius: var(--radius-lg); padding: var(--spacing-xl); box-shadow: var(--shadow-sm);">
                        <div style="margin-bottom: var(--spacing-md);">
                            <i class="fas fa-quote-left" style="font-size: 2rem; color: var(--color-primary);"></i>
                        </div>
                        <p style="color: var(--color-gray-dark); line-height: 1.8; margin-bottom: var(--spacing-lg);">
                            "<?php echo esc_html($testimonial['content']); ?>"
                        </p>
                        <div style="display: flex; align-items: center; gap: var(--spacing-md);">
                            <div style="width: 50px; height: 50px; background: var(--color-primary-light); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                                <i class="fas fa-user" style="color: var(--color-secondary);"></i>
                            </div>
                            <div>
                                <strong><?php echo esc_html($testimonial['author']); ?></strong>
                                <p style="margin: 0; font-size: 0.875rem; color: var(--color-gray);"><?php echo esc_html($testimonial['company']); ?></p>
                            </div>
                        </div>
                    </div>
                <?php endforeach; ?>
            </div>
        </div>
        
        <!-- 成为合作伙伴 -->
        <div class="become-partner" style="text-align: center;">
            <h2 style="margin-bottom: var(--spacing-md);"><?php esc_html_e('成为我们的合作伙伴', 'sysafari-logistics'); ?></h2>
            <p style="color: var(--color-gray-dark); margin-bottom: var(--spacing-xl); max-width: 600px; margin-left: auto; margin-right: auto;">
                <?php esc_html_e('无论您是货代同行、电商平台还是生产制造企业，我们都期待与您建立合作关系，共同发展，互利共赢。', 'sysafari-logistics'); ?>
            </p>
            <a href="<?php echo esc_url(home_url('/contact')); ?>" class="btn btn-secondary btn-lg">
                <?php esc_html_e('联系我们洽谈合作', 'sysafari-logistics'); ?>
            </a>
        </div>
        
    </div>
</section>

<style>
.industry-item:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-md);
    border-color: var(--color-primary);
}

.partner-logo:hover {
    background: var(--color-primary-light);
}

@media (max-width: 1024px) {
    .partner-industries > div:last-child {
        grid-template-columns: repeat(4, 1fr) !important;
    }
    
    .partner-logos > div:first-of-type {
        grid-template-columns: repeat(3, 1fr) !important;
    }
}

@media (max-width: 768px) {
    .partner-industries > div:last-child {
        grid-template-columns: repeat(3, 1fr) !important;
    }
    
    .partner-logos > div:first-of-type {
        grid-template-columns: repeat(2, 1fr) !important;
    }
    
    .partner-testimonials > div:last-child {
        grid-template-columns: 1fr !important;
    }
}
</style>

<?php
get_footer();
