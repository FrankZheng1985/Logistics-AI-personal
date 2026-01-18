<?php
/**
 * Template Name: 常见问题页面
 * 
 * FAQ常见问题页面
 *
 * @package Sysafari_Logistics
 */

get_header();

// FAQ数据
$faqs = array(
    array(
        'category' => '物流服务',
        'questions' => array(
            array(
                'q' => '你们提供哪些物流服务？',
                'a' => '我们提供海运、空运、陆运、仓储、报关清关、国际快递等全方位物流服务。无论是整箱、拼箱还是散货，我们都能为您提供专业的解决方案。'
            ),
            array(
                'q' => '你们的服务覆盖哪些国家和地区？',
                'a' => '我们的物流网络覆盖全球220多个国家和地区，包括北美、欧洲、亚太、中东、非洲等主要市场。'
            ),
            array(
                'q' => '你们能处理危险品运输吗？',
                'a' => '是的，我们具有危险品运输资质，可以处理各类危险品的国际运输。我们会根据货物特性提供专业的包装和运输方案，确保安全合规。'
            ),
        )
    ),
    array(
        'category' => '价格与报价',
        'questions' => array(
            array(
                'q' => '如何获取运费报价？',
                'a' => '您可以通过网站的"获取报价"页面提交询价请求，或直接联系我们的客服团队。我们会在1个工作日内为您提供详细的报价方案。'
            ),
            array(
                'q' => '运费是如何计算的？',
                'a' => '运费根据货物的重量、体积、起运地、目的地、运输方式等因素综合计算。海运通常按体积(CBM)或重量(KG)计费，空运按实际重量或体积重量（取大者）计费。'
            ),
            array(
                'q' => '有哪些付款方式？',
                'a' => '我们支持银行转账、信用证、PayPal等多种付款方式。对于长期合作客户，我们还提供月结等灵活的付款条件。'
            ),
        )
    ),
    array(
        'category' => '货物追踪',
        'questions' => array(
            array(
                'q' => '如何追踪我的货物？',
                'a' => '您可以在网站首页或"货物追踪"页面输入追踪号码，实时查看货物的运输状态。我们也会在货物状态更新时主动通知您。'
            ),
            array(
                'q' => '追踪信息多久更新一次？',
                'a' => '追踪信息通常在货物到达每个中转节点时更新。国际运输由于涉及多个环节，更新可能会有所延迟，请耐心等待。'
            ),
            array(
                'q' => '追踪显示"未找到"是什么原因？',
                'a' => '可能是货物刚刚发出，系统尚未更新信息。通常在发货后24-48小时内可以查询到。如果超过48小时仍无法查询，请联系客服。'
            ),
        )
    ),
    array(
        'category' => '时效与送达',
        'questions' => array(
            array(
                'q' => '海运通常需要多长时间？',
                'a' => '海运时效取决于起运港和目的港。例如：中国到美西约12-15天，到美东约22-28天，到欧洲约25-35天。具体时效请咨询客服。'
            ),
            array(
                'q' => '空运通常需要多长时间？',
                'a' => '空运通常3-7个工作日可以送达。紧急货物可选择特快空运服务，最快1-3天送达。'
            ),
            array(
                'q' => '如果货物延误怎么办？',
                'a' => '如遇货物延误，我们会第一时间通知您并说明原因。对于因我方原因造成的延误，我们会根据服务协议进行相应补偿。'
            ),
        )
    ),
    array(
        'category' => '保险与理赔',
        'questions' => array(
            array(
                'q' => '货物运输需要买保险吗？',
                'a' => '我们强烈建议为高价值货物购买运输保险。虽然我们尽最大努力确保货物安全，但保险能为您提供额外的保障。'
            ),
            array(
                'q' => '货物损坏或丢失如何理赔？',
                'a' => '如果货物在运输过程中发生损坏或丢失，请在收货时立即检查并保留证据，然后联系我们提交理赔申请。我们会协助您完成理赔流程。'
            ),
        )
    ),
);
?>

<div class="page-header">
    <div class="container">
        <h1><?php esc_html_e('常见问题', 'sysafari-logistics'); ?></h1>
    </div>
</div>

<?php sysafari_breadcrumbs(); ?>

<section class="section page-content">
    <div class="container">
        <div class="faq-intro" style="text-align: center; margin-bottom: var(--spacing-2xl); max-width: 700px; margin-left: auto; margin-right: auto;">
            <p style="color: var(--color-gray-dark); font-size: 1.125rem;">
                <?php esc_html_e('以下是客户经常咨询的问题，希望能帮助您快速找到答案。如果没有找到您需要的信息，请随时联系我们。', 'sysafari-logistics'); ?>
            </p>
        </div>
        
        <!-- 快速导航 -->
        <div class="faq-nav" style="display: flex; justify-content: center; gap: var(--spacing-md); margin-bottom: var(--spacing-2xl); flex-wrap: wrap;">
            <?php foreach ($faqs as $index => $category) : ?>
                <a href="#faq-category-<?php echo $index; ?>" class="btn btn-outline" style="font-size: 0.875rem;">
                    <?php echo esc_html($category['category']); ?>
                </a>
            <?php endforeach; ?>
        </div>
        
        <!-- FAQ列表 -->
        <div class="faq-list" style="max-width: 900px; margin: 0 auto;">
            <?php foreach ($faqs as $index => $category) : ?>
                <div class="faq-category" id="faq-category-<?php echo $index; ?>" style="margin-bottom: var(--spacing-2xl);">
                    <h2 style="color: var(--color-secondary); margin-bottom: var(--spacing-lg); padding-bottom: var(--spacing-sm); border-bottom: 2px solid var(--color-primary);">
                        <?php echo esc_html($category['category']); ?>
                    </h2>
                    
                    <div class="faq-accordion">
                        <?php foreach ($category['questions'] as $qindex => $faq) : ?>
                            <div class="faq-item" style="border: 1px solid var(--color-gray-light); border-radius: var(--radius-md); margin-bottom: var(--spacing-md); overflow: hidden;">
                                <div class="faq-question" style="padding: var(--spacing-md) var(--spacing-lg); background: var(--color-white); cursor: pointer; display: flex; justify-content: space-between; align-items: center;">
                                    <h4 style="margin: 0; font-size: 1rem; font-weight: 500;">
                                        <?php echo esc_html($faq['q']); ?>
                                    </h4>
                                    <span class="faq-icon" style="font-size: 1.25rem; color: var(--color-primary); transition: transform 0.3s;">
                                        <i class="fas fa-chevron-down"></i>
                                    </span>
                                </div>
                                <div class="faq-answer" style="padding: 0 var(--spacing-lg); max-height: 0; overflow: hidden; transition: all 0.3s ease; background: var(--color-light);">
                                    <div style="padding: var(--spacing-md) 0;">
                                        <p style="margin: 0; color: var(--color-gray-dark); line-height: 1.8;">
                                            <?php echo esc_html($faq['a']); ?>
                                        </p>
                                    </div>
                                </div>
                            </div>
                        <?php endforeach; ?>
                    </div>
                </div>
            <?php endforeach; ?>
        </div>
        
        <!-- 联系客服 -->
        <div class="faq-contact" style="background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%); border-radius: var(--radius-lg); padding: var(--spacing-2xl); text-align: center; margin-top: var(--spacing-2xl);">
            <h3 style="margin-bottom: var(--spacing-md);"><?php esc_html_e('没有找到答案？', 'sysafari-logistics'); ?></h3>
            <p style="margin-bottom: var(--spacing-lg);"><?php esc_html_e('我们的客服团队随时为您解答疑问', 'sysafari-logistics'); ?></p>
            <div style="display: flex; justify-content: center; gap: var(--spacing-md); flex-wrap: wrap;">
                <a href="<?php echo esc_url(home_url('/contact')); ?>" class="btn btn-secondary">
                    <i class="fas fa-envelope" style="margin-right: 8px;"></i>
                    <?php esc_html_e('在线留言', 'sysafari-logistics'); ?>
                </a>
                <a href="tel:<?php echo esc_attr(preg_replace('/[^0-9+]/', '', sysafari_get_option('company_phone', '+86 400-XXX-XXXX'))); ?>" class="btn" style="background: white; color: var(--color-dark);">
                    <i class="fas fa-phone-alt" style="margin-right: 8px;"></i>
                    <?php echo esc_html(sysafari_get_option('company_phone', '+86 400-XXX-XXXX')); ?>
                </a>
            </div>
        </div>
    </div>
</section>

<style>
.faq-item.active .faq-question {
    background: var(--color-light);
}

.faq-item.active .faq-icon {
    transform: rotate(180deg);
}

.faq-item.active .faq-answer {
    max-height: 500px;
}

.faq-question:hover {
    background: var(--color-light);
}
</style>

<script>
jQuery(document).ready(function($) {
    // FAQ手风琴效果
    $('.faq-question').on('click', function() {
        var $item = $(this).closest('.faq-item');
        
        // 关闭同类别的其他项
        $item.siblings('.faq-item.active').removeClass('active');
        
        // 切换当前项
        $item.toggleClass('active');
    });
    
    // 平滑滚动到类别
    $('.faq-nav a').on('click', function(e) {
        e.preventDefault();
        var target = $(this.hash);
        if (target.length) {
            $('html, body').animate({
                scrollTop: target.offset().top - 100
            }, 500);
        }
    });
});
</script>

<?php
get_footer();
